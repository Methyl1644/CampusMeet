from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from storage.database.models import Post, Team, User
from storage.database.shared.model import Base


@pytest.mark.parametrize("input_size", [13, 250])
def test_team_model_bounds_task_json_before_and_after_persistence(input_size):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tasks = [
        {"id": f"task-{index}", "title": f"任务 {index}", "done": False}
        for index in range(input_size)
    ]

    with factory() as session:
        session.add(
            User(
                id=1,
                email="owner@nju.edu.cn",
                password_hash="hash",
                nickname="owner",
                auth_status="verified",
            )
        )
        session.add(
            Post(
                id=1,
                title="增长测试小组",
                main_category="竞赛与项目",
                activity_name="增长测试小组",
                target_members=4,
                author_id=1,
            )
        )
        team = Team(
            id=1,
            post_id=1,
            owner_id=1,
            activity_name="增长测试小组",
            task_list=tasks,
        )

        assert len(team.task_list) == 12
        assert [task["id"] for task in team.task_list] == [
            f"task-{index}" for index in range(12)
        ]

        session.add(team)
        session.commit()
        session.expire(team, ["task_list"])

        persisted = session.scalar(select(Team.task_list).where(Team.id == team.id))
        assert len(persisted) == 12
        assert [task["id"] for task in persisted] == [
            f"task-{index}" for index in range(12)
        ]
