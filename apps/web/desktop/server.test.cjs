const assert = require('node:assert/strict')
const test = require('node:test')

const { contentTypeFor, safeAssetPath } = require('./server.cjs')

test('contentTypeFor returns browser-friendly types for bundled assets', () => {
  assert.equal(contentTypeFor('index.html'), 'text/html; charset=utf-8')
  assert.equal(contentTypeFor('app.js'), 'text/javascript; charset=utf-8')
  assert.equal(contentTypeFor('font.woff2'), 'font/woff2')
})

test('safeAssetPath keeps requests inside the bundled dist directory', () => {
  const dist = 'C:\\bundle\\dist'

  assert.equal(safeAssetPath(dist, '/assets/app.js'), 'C:\\bundle\\dist\\assets\\app.js')
  assert.equal(safeAssetPath(dist, '/../secret.txt'), null)
})
