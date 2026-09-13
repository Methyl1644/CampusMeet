import type { ExploreActivityCard, ExploreGroupCard } from '@shared/types'

export const exploreUser = {
  id: 'student-1',
  nickname: '林晓',
  avatar: null,
  major: '软件工程',
  grade: '2024级',
}

export const activityFixture: ExploreActivityCard = {
  id: 'activity-1', channel: 'organization',
  title: '跨学科校园人工智能与机器人创新实践挑战赛', short_title: '人工智能挑战赛',
  organizer: '计算机科学与技术系', edition: '2026 秋季', summary: '面向全校学生的人工智能创新实践。',
  content: '活动详情', source_url: null, source_status: 'verified', cover_url: '/images/ai-contest.jpg',
  cover_placeholder_key: 'activity:organization', location_name: '仙林校区计算机科学技术楼', campus_scope: '仙林校区',
  capacity: 40, registration_deadline: '2026-09-25T10:00:00+08:00', activity_start_at: '2026-10-03T09:30:00+08:00',
  activity_end_at: null, follower_count: 128, participant_count: 31, participant_preview: [exploreUser],
  participation_mode: 'open_team', favorite: false, followed: false, participation_state: 'available',
  tags: [{ tag_id: 'activity_ai', canonical_name: '人工智能', category: 'activity', display_color: '#4455aa' }],
  status: 'active',
  trust_badges: [{ kind: 'verified_organization', label: '认证组织', organization_name: '计算机科学与技术系' }],
  responsible_people: [],
}

export const groupFixture: ExploreGroupCard = {
  id: 'group-1', title: '寻找前端同学一起参加机器人挑战赛', description: '一起完成机器人控制台与展示页面。',
  source_type: 'user', kind: 'topic_team', purpose: 'team_recruitment', join_mode: 'application', topic_id: 'activity-1',
  main_category: '竞赛与项目', activity_name: '人工智能与机器人创新实践挑战赛', cover_url: null,
  cover_placeholder_key: 'category:competition-project', current_members: 3, target_members: 5,
  needed_roles: ['前端开发', '视觉设计'], weekly_hours: '每周 4 小时', school_scope: '仙林校区',
  deadline: '2026-09-28T20:00:00+08:00', risk_level: 'low', status: 'recruiting', author_id: exploreUser.id,
  author: exploreUser, bookmark: false, join_state: 'available', member_preview: [exploreUser],
  linked_activity: {
    id: 'activity-1', title: activityFixture.title, short_title: activityFixture.short_title,
    organizer: activityFixture.organizer, cover_url: activityFixture.cover_url,
    cover_placeholder_key: activityFixture.cover_placeholder_key, registration_deadline: activityFixture.registration_deadline,
    activity_start_at: activityFixture.activity_start_at, participation_mode: activityFixture.participation_mode, status: 'active',
  },
  tags: activityFixture.tags, collaborators: [], created_at: '2026-09-13T08:00:00+08:00',
}
