# Phase 6: Quick Start Checklist

**Use this checklist to track your progress through Phase 6 deployment.**

---

## 🎯 Before You Start

**Answer these questions:**

1. **Where will you deploy the backend?**
   - [ ] Docker (VPS/Cloud)
   - [ ] PaaS (Heroku, Render, Railway, Fly.io)
   - [ ] Serverless (AWS Lambda, Google Cloud Run)
   - [ ] Traditional VM (systemd service)
   - [ ] Other: _______________

2. **Where will you deploy the frontend?**
   - [ ] Static hosting (Netlify, Vercel, Cloudflare Pages)
   - [ ] CDN + Object Storage (S3+CloudFront, GCS)
   - [ ] Same server as backend (nginx)
   - [ ] Other: _______________

3. **What's your production domain?**
   - Backend API: `https://________________.com`
   - Frontend: `https://________________.com`

4. **Do you have production database ready?**
   - [ ] Yes, PostgreSQL running
   - [ ] No, need to set up

5. **Have you backed up your production database?**
   - [ ] Yes, backup created
   - [ ] No, need to backup
   - [ ] N/A (fresh install)

---

## ✅ Phase 6 Checklist

### Step 1: Stripe Billing Portal Configuration (30 min)

**📍 Location:** https://dashboard.stripe.com/settings/billing/portal

- [ ] Activate test link
- [ ] Enable "Allow customers to cancel subscriptions"
  - [ ] Set cancel mode to "At period end"
  - [ ] Optionally enable "Immediately"
- [ ] Enable "Allow customers to switch plans"
  - [ ] Set proration: "Always invoice immediately"
  - [ ] Add all 4 price IDs (Pro monthly/annual, Pro Plus monthly/annual)
- [ ] Enable "Allow customers to update payment methods"
- [ ] Disable "Allow customers to remove payment methods"
- [ ] Enable "Show invoice history"
- [ ] **Optional branding:**
  - [ ] Upload logo (512x512px PNG)
  - [ ] Set accent color
  - [ ] Set business name
  - [ ] Set support email
  - [ ] Add Terms of Service URL
  - [ ] Add Privacy Policy URL
- [ ] Test portal with test customer

**✅ Done when:** Portal loads and all features work in test mode

---

### Step 2: Business Information (10 min)

**📍 Location:** https://dashboard.stripe.com/settings/public

- [ ] Set business name
- [ ] Set support email
- [ ] Set support phone (optional)
- [ ] Set business website
- [ ] Set statement descriptor (e.g., "GEARSTACK")
- [ ] Configure tax settings (if needed)

**✅ Done when:** Business info saved in Stripe Dashboard

---

### Step 3: Environment Variables Checklist (15 min)

**Create a secure document with all production environment variables:**

#### Backend Variables
- [ ] `DATABASE_URL` (production PostgreSQL connection string)
- [ ] `SECRET_KEY` (new 32+ char random key - **don't reuse dev key!**)
- [ ] `ALLOWED_HOSTS` (production domains)
- [ ] `CORS_ORIGINS` (production frontend URLs)
- [ ] `ENVIRONMENT=production`
- [ ] `STRIPE_SECRET_KEY` (use `sk_test_...` first, then switch to `sk_live_...`)
- [ ] `STRIPE_PUBLISHABLE_KEY` (use `pk_test_...` first, then switch to `pk_live_...`)
- [ ] `STRIPE_WEBHOOK_SECRET` (from production webhook endpoint)
- [ ] All 4 `STRIPE_*_PRICE_ID` variables

#### Frontend Variables
- [ ] `VITE_API_PROXY_URL` (production backend URL)
- [ ] `VITE_STRIPE_PUBLISHABLE_KEY` (use `pk_test_...` first, then switch to `pk_live_...`)
- [ ] All 4 `VITE_STRIPE_*_PRICE_ID` variables

**✅ Done when:** All variables documented and ready to set

---

### Step 4: Database Migration (30 min)

**⚠️ CRITICAL:** Backup database first!

#### Backup
```bash
# Create backup
pg_dump -h HOST -U USER -d DATABASE > backup_$(date +%Y%m%d_%H%M%S).sql
```

- [ ] Backup created and verified
- [ ] Backup stored in safe location

#### Run Migration
```bash
# Via Docker
docker exec -it gear-stack-app python migrations/047_add_billing_tables.py upgrade

# Or via venv
python migrations/047_add_billing_tables.py upgrade
```

- [ ] Migration completed successfully
- [ ] Verified tables created: `subscriptions`, `stripe_webhook_events`, `subscription_history`
- [ ] Verified existing premium users migrated (check with SQL query)

**✅ Done when:** Migration successful and verified

---

### Step 5: Deploy Backend (varies)

**Method:** _______________ (Docker/PaaS/VM/Other)

- [ ] Quality checks passed:
  - [ ] `mypy` (no type errors)
  - [ ] `black --check` (formatting OK)
  - [ ] `pytest` (all tests pass)
- [ ] Environment variables set in production
- [ ] Code deployed to production
- [ ] Service started/restarted
- [ ] Health check passed: `curl https://api.yourdomain.com/health`
- [ ] Billing endpoint accessible (requires auth)
- [ ] Logs checked (no errors)

**✅ Done when:** Backend responding correctly in production

---

### Step 6: Deploy Frontend (varies)

**Method:** _______________ (Static/CDN/Server/Other)

- [ ] Quality checks passed:
  - [ ] `pnpm type-check` (no TypeScript errors)
  - [ ] `pnpm lint` (no ESLint errors)
- [ ] Production build created: `pnpm build`
- [ ] Environment variables set (if applicable)
- [ ] Built files deployed
- [ ] Homepage loads: `https://yourdomain.com`
- [ ] Billing page loads: `https://yourdomain.com/billing`
- [ ] No console errors (check browser DevTools)
- [ ] Responsive design works (mobile/tablet/desktop)

**✅ Done when:** Frontend loading correctly in production

---

### Step 7: Webhook Connectivity (15 min)

**📍 Location:** https://dashboard.stripe.com/webhooks

- [ ] Verify endpoint URL: `https://api.gear-stack.ovh/api/billing/webhooks/stripe`
- [ ] Verify events selected (6 total):
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.created`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `invoice.payment_succeeded`
  - [ ] `invoice.payment_failed`
- [ ] Send test webhook from Stripe Dashboard
- [ ] Verify 200 OK response
- [ ] Check database: webhook event logged
- [ ] Check backend logs: webhook processed

**✅ Done when:** Test webhook received and processed successfully

---

### Step 8: Smoke Tests (60 min)

**⚠️ Use TEST mode API keys first!**

#### Test 1: Checkout Flow
- [ ] Create test user account
- [ ] Navigate to `/billing`
- [ ] See FREE tier status
- [ ] Click "Upgrade to Pro"
- [ ] Redirected to Stripe Checkout
- [ ] Complete payment with test card `4242 4242 4242 4242`
- [ ] Redirected to `/billing/success`
- [ ] See "Subscription Activated!" message
- [ ] Return to `/billing`
- [ ] See Pro tier status

#### Test 2: Billing Portal
- [ ] Click "Manage Subscription"
- [ ] Redirected to Stripe Billing Portal
- [ ] Can view subscription
- [ ] Can update payment method
- [ ] Can view invoices
- [ ] Can cancel subscription

#### Test 3: Plan Switch
- [ ] In portal, switch Pro → Pro Plus (or vice versa)
- [ ] See new plan in app

#### Test 4: Cancellation
- [ ] Cancel subscription (at period end)
- [ ] Return to app
- [ ] See warning: "Subscription will cancel on [date]"

#### Test 5: Upgrade Prompts
- [ ] Log in as FREE user
- [ ] See UpgradePromptBanner on dashboard
- [ ] Can dismiss banner
- [ ] Banner stays dismissed

#### Test 6: Subscription Badge
- [ ] Go to profile page
- [ ] See subscription badge (Free/Pro/Pro Plus)
- [ ] Badge shows correct icon

**✅ Done when:** All 6 tests pass without errors

---

### Step 9: Monitoring Setup (15 min)

**Set up monitoring for first 24 hours:**

- [ ] Bookmark Stripe Dashboard: https://dashboard.stripe.com/events
- [ ] Set up database query for metrics (see deployment guide)
- [ ] Configure backend log monitoring
- [ ] Set up alerts for errors (optional)
- [ ] Document how to check webhook events table
- [ ] Document how to check subscription metrics

**✅ Done when:** Can monitor webhooks, subscriptions, and errors

---

### Step 10: Go Live! (Production API Keys)

**⚠️ CRITICAL:** Only do this after all tests pass!

#### Pre-Switch Checklist
- [ ] All smoke tests passed (Step 8)
- [ ] Webhook connectivity verified (Step 7)
- [ ] No errors in logs
- [ ] Monitoring in place (Step 9)

#### Switch to Production Keys

**Backend:**
- [ ] Update `STRIPE_SECRET_KEY` to `sk_live_...`
- [ ] Update `STRIPE_PUBLISHABLE_KEY` to `pk_live_...`
- [ ] Update `STRIPE_WEBHOOK_SECRET` (if changed)
- [ ] Restart backend service

**Frontend:**
- [ ] Update `VITE_STRIPE_PUBLISHABLE_KEY` to `pk_live_...`
- [ ] Rebuild: `pnpm build`
- [ ] Redeploy frontend

#### Verification
- [ ] Stripe Dashboard shows "Live mode" (toggle in top-left)
- [ ] Create real checkout session (⚠️ will charge real money!)
- [ ] Complete test purchase (can refund immediately)
- [ ] Verify real subscription created

**✅ Done when:** Production API keys active and verified

---

### Step 11: Announce & Monitor (24 hours)

#### Launch
- [ ] Write user announcement
- [ ] Publish announcement (email, in-app, blog, social media)
- [ ] Update documentation/help center
- [ ] Brief support team (if applicable)

#### Monitor First 24 Hours
- [ ] Check webhook processing every hour
- [ ] Monitor for errors in logs
- [ ] Track first real subscriptions
- [ ] Respond to support requests promptly
- [ ] Monitor payment failure rate
- [ ] Check Stripe Dashboard for issues

**✅ Done when:** 24 hours passed without critical issues

---

## 🎉 Success Criteria

**Phase 6 is COMPLETE when:**

1. ✅ All 11 steps completed
2. ✅ Production API keys active
3. ✅ Real checkout flow working
4. ✅ Webhooks processing correctly
5. ✅ First real subscription processed
6. ✅ Monitoring in place
7. ✅ No critical errors in 24 hours
8. ✅ User announcement published

---

## 🆘 Need Help?

**Full deployment guide:**
- See: `docs/deployment/phase-6-production-deployment-guide.md`

**Testing guides:**
- Cancellation: `docs/testing/billing-cancellation-test-guide.md`
- Performance: `docs/optimization/billing-performance-recommendations.md`

**Rollback procedures:**
- See deployment guide Step "Rollback Procedures"

**Stripe Support:**
- Dashboard: https://dashboard.stripe.com
- Support: https://support.stripe.com
- Status: https://status.stripe.com

---

**Current Step:** Step 1 - Configure Stripe Billing Portal

**Next:** Go to https://dashboard.stripe.com/settings/billing/portal 🚀
