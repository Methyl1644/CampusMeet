import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from api import agent as agent_api
from services.content import seed_content_catalog
from services.publish_context import missing_fields, publish_context, reconcile_draft, merge_tag_ids
from storage.database.models import Notification, Post, PostTag, Topic, TopicTag, TopicCollaborator, UploadRecord, User
from storage.database.shared.model import Base
from tools import post_tools


@pytest.fixture
def sessions(monkeypatch):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        seed_content_catalog(session)
        session.add_all([User(id=901, email='publish@nju.edu.cn', password_hash='test', nickname='发布者', auth_status='verified'), User(id=902, email='other@nju.edu.cn', password_hash='test', nickname='其他人', auth_status='verified')])
        session.add(Topic(id=901, channel='official', title='校园编程活动', short_title='编程', organizer='校园', organizer_key='campus', canonical_event_key='publish-test', edition='2026', summary='活动简介', content='活动说明', created_by=901, participation_mode='open_team'))
        session.flush()
        session.add(TopicTag(topic_id=901, tag_id='skill_python'))
        session.add(TopicCollaborator(topic_id=901, user_id=901, role='manager', status='active', granted_by=901))
        session.commit()
    monkeypatch.setattr(post_tools, 'get_session', factory)
    monkeypatch.setattr(agent_api, 'get_session', factory)
    yield factory
    engine.dispose()


def context(sessions, kind='casual_invitation', topic=''):
    with sessions() as session:
        return publish_context(session, session.get(User, 901), kind, topic)


def draft():
    return dict(activity_name='周末羽毛球', target_members=4, needed_roles=[], weekly_hours='周六下午', school_scope='仙林体育馆', description='一起运动', deadline='2026-12-01')


def payload(**changes):
    return dict(user_id='901', title='周末羽毛球', description='一起运动', main_category='校园生活', activity_name='周末羽毛球', target_members=4, needed_roles='', client_request_id='publish-test-key-0001', **changes)


def test_context_enforces_topic_policy_and_inherits_tags(sessions):
    value = context(sessions, 'topic_team', '901')
    assert value['allowed_purposes'] == ['team_recruitment', 'discussion']
    assert value['inherited_tags'][0]['tag_id'] == 'skill_python'
    with sessions() as session:
        session.get(Topic, 901).participation_mode = 'official_signup'
        session.commit()
    newer = context(sessions, 'topic_team', '901')
    assert newer['revision'] != value['revision']
    assert newer['allowed_purposes'] == ['official_signup', 'discussion']
    with sessions() as session:
        other = publish_context(session, session.get(User, 902), 'topic_team', '901')
        assert other['allowed_purposes'] == ['discussion']


@pytest.mark.parametrize('status', ['pending', 'unknown', 'skipped'])
def test_unconfirmed_fields_never_complete(status):
    value = draft()
    states = {'needed_roles': {'status': 'none'}, 'school_scope': {'status': status}}
    assert 'school_scope' in missing_fields(value, states, 'casual_invitation', 'team_recruitment')


def test_explicit_no_role_is_valid_but_empty_role_is_not():
    assert not missing_fields(draft(), {'needed_roles': {'status': 'none'}}, 'casual_invitation', 'team_recruitment')
    assert 'needed_roles' in missing_fields(draft(), {}, 'casual_invitation', 'team_recruitment')
    value = {**draft(), 'needed_roles': ['待定']}
    assert 'needed_roles' in missing_fields(value, {}, 'casual_invitation', 'team_recruitment')


def test_ai_cannot_override_activity_or_claim_false_completion(sessions):
    result = reconcile_draft({'draft': {**draft(), 'activity_name': '伪造活动', 'target_members': 0, 'topic_id': '999'}, 'is_complete': True}, {}, context(sessions, 'topic_team', '901'), 'team_recruitment')
    assert result['draft']['activity_name'] == '校园编程活动'
    assert 'topic_id' not in result['draft']
    assert not result['is_complete']


def test_tag_merge_preserves_inherited_and_rejects_overflow():
    assert merge_tag_ids(['a'], ['b', 'a'], ['c']) == ['a', 'b', 'c']
    with pytest.raises(ValueError):
        merge_tag_ids(['a'], list('bcdefghij'))


def test_skip_cannot_be_used_as_required_description():
    assert missing_fields({'activity_name': '经验交流', 'description': '跳过'}, {}, 'casual_invitation', 'discussion') == ['description']


def test_publish_retry_is_one_post_one_notification(sessions):
    first = json.loads(post_tools.create_post.invoke(payload(kind='topic_team', topic_id='901')))
    second = json.loads(post_tools.create_post.invoke(payload(kind='topic_team', topic_id='901')))
    assert first['success'], first
    assert second['post']['id'] == first['post']['id']
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Post).where(Post.author_id == 901)) == 1
        assert session.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == 901)) == 1
        post = session.scalar(select(Post).where(Post.author_id == 901))
        assert post.activity_name == '校园编程活动'
        assert session.scalar(select(PostTag.tag_id).where(PostTag.post_id == post.id)) == 'skill_python'


@pytest.mark.parametrize('owner,status,private,success', [(901, 'completed', False, True), (902, 'completed', False, False), (901, 'pending', False, False), (901, 'completed', True, False)])
def test_cover_ownership_completion_and_atomic_publish(sessions, monkeypatch, owner, status, private, success):
    monkeypatch.setenv('OBJECT_STORAGE_PUBLIC_BASE_URL', 'https://media.example.test')
    with sessions() as session:
        session.add(UploadRecord(id='cover-test', owner_id=owner, purpose='post_cover', object_key='public/post-covers/test.png', original_filename='test.png', mime_type='image/png', expected_size=123, status=status, private=private))
        session.commit()
    result = json.loads(post_tools.create_post.invoke(payload(cover_upload_id='cover-test')))
    assert result['success'] is success, result
    with sessions() as session:
        created = session.scalar(select(Post).where(Post.author_id == 901))
        assert bool(created) is success
        if success:
            assert created.cover_url == 'https://media.example.test/public/post-covers/test.png'
            assert session.get(UploadRecord, 'cover-test').status == 'attached'


def test_discussion_freeform_answer_completes_without_remote_call(sessions, monkeypatch):
    monkeypatch.setattr(agent_api, 'invoke_tool', lambda *a, **k: pytest.fail('unnecessary model call'))
    value = context(sessions, 'topic_team', '901')
    result = agent_api.post_draft({'message': '想请教编程比赛的准备经验', 'draft': {'activity_name': value['activity']['title']}, 'kind': 'topic_team', 'topic_id': '901', 'purpose': 'discussion', 'publish_context_revision': value['revision']}, '901')
    assert result['data']['is_complete']
    assert result['data']['draft']['description'] == '想请教编程比赛的准备经验'


def test_stale_context_rejected_before_model_call(sessions, monkeypatch):
    monkeypatch.setattr(agent_api, 'invoke_tool', lambda *a, **k: pytest.fail('stale request reached model'))
    with pytest.raises(HTTPException) as error:
        agent_api.post_draft({'message': '找伙伴', 'kind': 'topic_team', 'topic_id': '901', 'purpose': 'discussion', 'publish_context_revision': 'outdated'}, '901')
    assert error.value.status_code == 409


def test_migration_upgrade_downgrade_upgrade(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect
    config = Config('alembic.ini')
    url = 'sqlite:///' + str(tmp_path / 'migration.db').replace('\\', '/')
    config.set_main_option('sqlalchemy.url', url)
    command.upgrade(config, 'head')
    engine = create_engine(url)
    assert 'client_request_id' in {column['name'] for column in inspect(engine).get_columns('posts')}
    command.downgrade(config, '20260913_16')
    assert 'client_request_id' not in {column['name'] for column in inspect(engine).get_columns('posts')}
    command.upgrade(config, 'head')
    assert 'uq_posts_author_request' in {index['name'] for index in inspect(engine).get_indexes('posts')}
    engine.dispose()
