export const auditsQueryKeys = {
  all: ['benchify', 'audits'] as const,
  list: (cursor?: string) => ['benchify', 'audits', 'list', cursor] as const,
} as const
