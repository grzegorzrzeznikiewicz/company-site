FROM mcr.microsoft.com/playwright:v1.62.1-noble@sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e

WORKDIR /tests
COPY wordpress/qa/e2e/package.json wordpress/qa/e2e/package-lock.json ./
RUN npm ci --ignore-scripts
COPY wordpress/qa/e2e/playwright.config.ts ./
COPY wordpress/qa/e2e/timeout-policy.tsconfig.json ./
COPY wordpress/qa/e2e/specs ./specs
CMD ["npm", "test"]
