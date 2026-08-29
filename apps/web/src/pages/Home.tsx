import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, TrendingUp } from 'lucide-react'
import { getPosts, type PostListParams } from '@/api/posts'
import type { Post } from '@shared/types'
import { HOME_TABS } from '@shared/constants'
import PostCard from '@/components/PostCard'
import EmptyState from '@/components/EmptyState'
import Loading from '@/components/Loading'
import { useToast } from '@/components/Toast'

export default function Home() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [activeTab, setActiveTab] = useState<string>('recommend')
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const fetchPosts = async () => {
      setLoading(true)
      try {
        const res = await getPosts({ tab: activeTab as PostListParams['tab'], page: 1, page_size: 20 })
        if (!cancelled) setPosts(res.list)
      } catch {
        if (!cancelled) {
          setPosts([])
          showToast('加载失败，请稍后重试', 'error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPosts()
    return () => { cancelled = true }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      {/* 顶部 Banner */}
      <div className="mb-4 overflow-hidden rounded-xl bg-gradient-to-r from-primary-500 to-blue-400 p-4 text-white">
        <div className="flex items-center gap-2">
          <TrendingUp size={20} />
          <span className="text-sm font-medium">热门活动推荐</span>
        </div>
        <p className="mt-1 text-xs text-primary-50">发现正在招募的队伍，或发布你自己的需求</p>
      </div>

      {/* Tab 切换 */}
      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-gray-200">
        {HOME_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 帖子列表 */}
      {loading ? (
        <Loading />
      ) : posts.length === 0 ? (
        <EmptyState
          title="还没有帖子"
          description="去发布第一个组队需求吧"
          action={
            <button onClick={() => navigate('/publish')} className="btn-primary">
              <Plus size={16} />
              发布需求
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      {/* 桌面端浮动发布按钮 */}
      <button
        onClick={() => navigate('/publish')}
        className="fixed bottom-6 right-6 hidden h-12 w-12 items-center justify-center rounded-full bg-primary-600 text-white shadow-lg transition-transform hover:scale-110 md:flex"
      >
        <Plus size={24} />
      </button>
    </div>
  )
}
