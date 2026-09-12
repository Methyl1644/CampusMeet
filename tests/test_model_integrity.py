from sqlalchemy import create_engine, inspect

from storage.database.models import Application, Conversation, Message, Post, Team, TeamMember


def _foreign_keys(table) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    return {
        (
            tuple(element.parent.name for element in constraint.elements),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
        )
        for constraint in table.foreign_key_constraints
    }


def test_core_collaboration_models_declare_relational_integrity():
    assert (("author_id",), "users", ("id",)) in _foreign_keys(Post.__table__)
    assert (("topic_id",), "topics", ("id",)) in _foreign_keys(Post.__table__)

    assert (("post_id",), "posts", ("id",)) in _foreign_keys(Application.__table__)
    assert (("applicant_id",), "users", ("id",)) in _foreign_keys(Application.__table__)

    conversation_fks = _foreign_keys(Conversation.__table__)
    assert (("post_id",), "posts", ("id",)) in conversation_fks
    assert (("post_author_id",), "users", ("id",)) in conversation_fks
    assert (("applicant_id",), "users", ("id",)) in conversation_fks
    assert (("application_id",), "applications", ("id",)) in conversation_fks

    assert (("conversation_id",), "conversations", ("id",)) in _foreign_keys(Message.__table__)
    assert (("sender_id",), "users", ("id",)) in _foreign_keys(Message.__table__)
    assert (("post_id",), "posts", ("id",)) in _foreign_keys(Team.__table__)
    assert (("team_id",), "teams", ("id",)) in _foreign_keys(TeamMember.__table__)
    assert (("user_id",), "users", ("id",)) in _foreign_keys(TeamMember.__table__)


def test_active_application_and_conversation_retry_guards_exist(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'constraints.db'}")
    from storage.database.shared.model import Base

    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    application_indexes = {index["name"]: index for index in inspector.get_indexes("applications")}
    assert application_indexes["uq_active_application_per_post_user"]["unique"] == 1

    conversation_constraints = {
        constraint["name"]: constraint
        for constraint in inspector.get_unique_constraints("conversations")
    }
    assert conversation_constraints["uq_conversation_application"]["column_names"] == ["application_id"]
