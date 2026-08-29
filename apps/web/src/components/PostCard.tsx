import { Link } from 'react-router-dom'
import { Clock, Users } from 'lucide-react'
import type { Post } from '@shared/types'
import SourceBadge from './SourceBadge'
import RiskTag from './RiskTag'
import StatusBadge from './StatusBadge'

export default function PostCard({ post }: { post: Post }) {
  return (
    <Link
      to={`/posts/${post.id}`}
      className="card block transition-shadow hover:shadow-md"
    >
      {/* 顶部：来源徽章 + 分类 + 状态 */}
      <div className="mb-2 flex items-center gap-2">
        <SourceBadge type={post.source_type} />
        <span className="text-xs text-gray-500">{post.main_category}</span>
        <StatusBadge status={post.status} />
        {post.risk_level !== 'low' && <RiskTag level={post.risk_level} />}
      </div>

      {/* 标题 */}
      <h3 className="mb-2 line-clamp-2 text-sm font-semibold text-gray-900">
        {post.title}
      </h3>

      {/* 缺少角色 + 截止时间 */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
        {post.needed_roles.length > 0 && (
          <span className="flex items-center gap-1">
            <Users size={14} />
            缺少：{post.needed_roles.join(' ')}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Clock size={14} />
          截止 {post.deadline}
        </span>
      </div>

      {/* 匹配度 + 申请按钮 */}
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
        {post.match_score !== undefined ? (
          <span className="text-sm font-medium text-primary-600">
            匹配度 {post.match_score}%
          </span>
        ) : (
          <span className="text-xs text-gray-400">
            {post.current_members}/{post.target_members} 人
          </span>
        )}
        {post.status === 'recruiting' && (
          <span className="rounded-md bg-primary-50 px-3 py-1 text-xs font-medium text-primary-600">
            申请
          </span>
        )}
      </div>
    </Link>
  )
}
