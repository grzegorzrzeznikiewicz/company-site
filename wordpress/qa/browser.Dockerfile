FROM mcr.microsoft.com/playwright:v1.54.2-noble@sha256:18b4bcff4f8ba0ac8c44b09f09def6a4f6cb8579e5f26381c21f38b50935d5d8

WORKDIR /tests
COPY wordpress/qa/e2e/package.json wordpress/qa/e2e/package-lock.json ./
RUN npm ci --ignore-scripts
COPY wordpress/qa/e2e/playwright.config.ts ./
COPY wordpress/qa/e2e/timeout-policy.tsconfig.json ./
COPY wordpress/qa/e2e/specs ./specs
CMD ["npm", "test"]
