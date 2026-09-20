const fs = require('node:fs')
const http = require('node:http')
const https = require('node:https')
const path = require('node:path')

const API_ORIGIN = 'https://campusmate-api-i3bf.onrender.com'

const CONTENT_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

function contentTypeFor(filePath) {
  return CONTENT_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream'
}

function safeAssetPath(distDir, requestPath) {
  let decoded
  try {
    decoded = decodeURIComponent(requestPath)
  } catch {
    return null
  }

  const root = path.resolve(distDir)
  const candidate = path.resolve(root, `.${decoded}`)
  return candidate === root || candidate.startsWith(`${root}${path.sep}`) ? candidate : null
}

function proxyApi(req, res) {
  const target = new URL(req.url, API_ORIGIN)
  const headers = { ...req.headers, host: target.host }
  delete headers.origin
  delete headers.referer

  const upstream = https.request(
    target,
    { method: req.method, headers, timeout: 90000 },
    (upstreamResponse) => {
      res.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers)
      upstreamResponse.pipe(res)
    },
  )

  upstream.on('timeout', () => upstream.destroy(new Error('API request timed out')))
  upstream.on('error', (error) => {
    if (res.headersSent) {
      res.destroy(error)
      return
    }
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ code: 'DESKTOP_API_UNAVAILABLE', message: '线上服务暂时不可用，请稍后重试' }))
  })
  req.pipe(upstream)
}

function serveAsset(distDir, req, res) {
  const requestUrl = new URL(req.url, 'http://127.0.0.1')
  const requestedPath = requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname
  const assetPath = safeAssetPath(distDir, requestedPath)
  const filePath = assetPath && fs.existsSync(assetPath) && fs.statSync(assetPath).isFile()
    ? assetPath
    : path.join(distDir, 'index.html')

  fs.readFile(filePath, (error, data) => {
    if (error) {
      res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('CampusMeet desktop assets are unavailable.')
      return
    }
    res.writeHead(200, {
      'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
      'Content-Type': contentTypeFor(filePath),
    })
    res.end(data)
  })
}

function startDesktopServer(distDir) {
  const server = http.createServer((req, res) => {
    if (req.url === '/api' || req.url.startsWith('/api/')) {
      proxyApi(req, res)
      return
    }
    serveAsset(distDir, req, res)
  })

  return new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      resolve({ server, url: `http://127.0.0.1:${address.port}` })
    })
  })
}

module.exports = { contentTypeFor, safeAssetPath, startDesktopServer }
