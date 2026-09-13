export interface HomeFeedRequestGate {
  begin: () => number
  commit: (requestId: number, transition: () => void) => boolean
  dispose: () => void
}

export function createHomeFeedRequestGate(): HomeFeedRequestGate {
  let latestRequestId = 0
  let disposed = false

  return {
    begin() {
      latestRequestId += 1
      return latestRequestId
    },
    commit(requestId, transition) {
      if (disposed || requestId !== latestRequestId) {
        return false
      }

      transition()
      return true
    },
    dispose() {
      disposed = true
    },
  }
}
