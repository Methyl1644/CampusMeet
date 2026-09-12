import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: [
      'src/pages/authFlow.test.ts',
      'src/components/onboarding/onboardingState.test.ts',
      'src/router/authRouting.test.ts',
    ],
  },
})
