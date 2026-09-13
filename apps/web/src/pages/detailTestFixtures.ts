import type { ExploreActivityDetail, ExploreGroupDetail, Team, User } from '@shared/types'
import { activityFixture, exploreUser, groupFixture } from '@/components/explore/exploreTestFixtures'

export const viewerFixture: User = {
  id: 'viewer-1',
  nickname: '周宁',
  avatar: '',
  auth_status: 'campus_verified',
  email: 'viewer@nju.edu.cn',
  skills: [],
  onboarding_step: 6,
  onboarding_completed: true,
  interests: [],
  looking_for: [],
  availability: {},
  profile_visibility: {
    major: true,
    grade: true,
    interests: true,
    skills: true,
    availability: true,
    contact: false,
  },
}

export const officialSignupGroup: ExploreGroupDetail = {
  ...groupFixture,
  id: 'official-group',
  title: '人工智能挑战赛官方报名',
  purpose: 'official_signup',
  join_mode: 'direct',
}

export const discussionGroup: ExploreGroupDetail = {
  ...groupFixture,
  id: 'discussion-group',
  title: '挑战赛经验交流',
  purpose: 'discussion',
  join_mode: 'none',
}

export const activityDetailFixture: ExploreActivityDetail = {
  ...activityFixture,
  summary: '面向全校学生的人工智能创新实践，鼓励跨专业协作。',
  content: '第一部分：活动介绍。\n\n第二部分：提交要求与评审安排。',
  responsible_people: [
    { user_id: 'manager-1', nickname: '陈老师', role: 'manager', badge: '活动负责人' },
  ],
  related_groups: [groupFixture, officialSignupGroup, discussionGroup],
}

export const groupDetailFixture: ExploreGroupDetail = {
  ...groupFixture,
  author_id: exploreUser.id,
  description: '我们希望一起完成机器人控制台、展示页面和现场答辩。',
  collaborators: [
    { user_id: 'helper-1', nickname: '王晨', role: 'application_manager', badge: '申请管理员' },
  ],
}

export const teamFixture: Team = {
  id: 'team-1',
  post_id: groupFixture.id,
  activity_name: groupFixture.activity_name,
  owner_id: exploreUser.id,
  status: 'active',
  members: [
    {
      user: {
        id: exploreUser.id,
        nickname: exploreUser.nickname,
        avatar: undefined,
        auth_status: 'campus_verified',
        major: exploreUser.major ?? undefined,
        grade: exploreUser.grade ?? undefined,
      },
      suggested_role: '队长',
      member_role: 'owner',
    },
  ],
  division_of_labor: [
    { role: '前端开发', responsibilities: '完成控制台界面', member_id: exploreUser.id },
  ],
  meeting_agenda: [{ id: 'agenda-1', content: '确认方案', done: false }],
  task_list: [{ id: 'task-1', title: '完成原型', assignee_name: exploreUser.nickname, done: false }],
  risk_reminders: ['留出联调时间'],
  contact_info: [{ user_id: exploreUser.id, nickname: exploreUser.nickname, wechat: 'campusmate' }],
  created_at: '2026-09-13T08:00:00+08:00',
}
