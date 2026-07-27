// modules/auth/validation/acceptInvite.schema.ts
import { z } from 'zod'

export const acceptInviteSchema = z.object({
  token: z.string().min(1, 'Token is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  passwordConfirmation: z.string(),
}).refine((data) => data.password === data.passwordConfirmation, {
  message: 'Passwords must match',
  path: ['passwordConfirmation'],
})

export type AcceptInviteFormData = z.infer<typeof acceptInviteSchema>
