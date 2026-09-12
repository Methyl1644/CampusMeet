import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../../packages/shared/src'),
    },
  },
  test: {
    include: [
      'src/pages/authFlow.test.ts',
      'src/pages/Login.test.tsx',
      'src/components/onboarding/ChoiceChips.test.tsx',
      'src/components/onboarding/onboardingState.test.ts',
      'src/router/authRouting.test.ts',
      'src/router/authRouting.integration.test.tsx',
      'src/store/authStore.test.ts',
      'src/api/home.test.ts',
      'src/features/home/HomeFeedContext.test.tsx',
      'src/components/navigation/Navbar.test.tsx',
    ],
  },
})
