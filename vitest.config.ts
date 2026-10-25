/// <reference types="vitest" />
import { getViteConfig } from "astro/config";

export default getViteConfig({
  test: {
    include: ["src/**/*.test.ts"],
    // テストは Task 4 以降で足す。それまでは 0 件でも失敗にしない
    passWithNoTests: true,
  },
});
