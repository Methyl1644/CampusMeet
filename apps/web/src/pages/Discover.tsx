import { useState, useEffect, useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { getPosts, type PostListParams } from '@/api/posts'
import type { Post, MainCategory } from '@shared/types'
import { MAIN_CATEGORIES, SORT_OPTIONS, COMMON_SKILLS } from '@shared/constants'
import PostCard from '@/components/PostCard'
import EmptyState from '@/components/EmptyState'
import Loading from '@/components/Loading'
import { useToast } from '@/components/Toast'

export default function Discover() {
  const { showToast } = useToast()
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState<MainCategory | ''>('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [sort, setSort] = useState<string>('latest')
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    try {
      const params: PostListParams = {
        keyword: keyword || undefined,
        category: category || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        sort: sort as PostListParams['sort'],
        page: 1,
        page_size: 30,
      }
      const res = await getPosts(params)
      setPosts(res.list)
    } catch {
      setPosts([])
      showToast('搜索失败，请稍后重试', 'error')
    } finally {
      setLoading(false)
    }
  }, [keyword, category, selectedTags, sort]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = setTimeout(fetchPosts, 300)
    return () => clearTimeout(timer)
  }, [fetchPosts])

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    )
  }

  return (
    <div>
      {/* 搜索栏 */}
      <div className="mb-4">
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索组队帖、活动名、关键词..."
            className="input-base pl-10"
          />
          {keyword && (
            <button
              onClick={() => setKeyword('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 分类筛选 */}
      <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
        <button
          onClick={() => setCategory('')}
          className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            category === '' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          全部分类
        </button>
        {MAIN_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              category === cat ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 标签筛选 */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {COMMON_SKILLS.slice(0, 12).map((tag) => (
          <button
            key={tag}
            onClick={() => toggleTag(tag)}
            className={`rounded-md border px-2 py-0.5 text-xs transition-colors ${
              selectedTags.includes(tag)
                ? 'border-primary-400 bg-primary-50 text-primary-600'
                : 'border-gray-200 text-gray-500'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {/* 排序 */}
      <div className="mb-4 flex items-center gap-3 border-b border-gray-200 pb-2">
        <span className="text-xs text-gray-400">排序：</span>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setSort(opt.key)}
            className={`text-xs font-medium transition-colors ${
              sort === opt.key ? 'text-primary-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* 结果列表 */}
      {loading ? (
        <Loading />
      ) : posts.length === 0 ? (
        <EmptyState title="没有找到符合条件的帖子" description="试试调整筛选条件或搜索关键词" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  )
}
