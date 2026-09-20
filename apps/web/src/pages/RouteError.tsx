import { AlertCircle, ArrowLeft, Home } from 'lucide-react'
import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom'

export default function RouteError({ notFound = false }: { notFound?: boolean }) {
  const routeError = useRouteError()
  const missing = notFound || (isRouteErrorResponse(routeError) && routeError.status === 404)
  const title = missing ? '这个页面没有找到' : '页面暂时无法打开'
  const message = missing
    ? '链接可能已失效，也可以从首页或探索页重新进入。'
    : '你的操作没有丢失，请返回上一页后重试。'

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper-warm px-5 py-12">
      <section className="w-full max-w-lg border-y border-stone bg-paper px-6 py-12 text-center sm:px-10">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary-100 text-primary-700">
          <AlertCircle aria-hidden="true" className="size-6" />
        </span>
        <p className="section-label mx-auto mt-5 w-fit">梧桐遇 CampusMeet</p>
        <h1 className="mt-4 text-2xl font-semibold text-ink">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-ink-muted">{message}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button type="button" className="btn-secondary" onClick={() => window.history.back()}>
            <ArrowLeft aria-hidden="true" className="size-4" />返回上一页
          </button>
          <Link to="/home" className="btn-primary">
            <Home aria-hidden="true" className="size-4" />回到首页
          </Link>
        </div>
      </section>
    </main>
  )
}
