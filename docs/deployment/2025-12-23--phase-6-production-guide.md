# Phase 6: Production Deployment Guide

**Status:** 🚧 IN PROGRESS
**Last Updated:** 2025-12-23

---

## 📋 Pre-Deployment Checklist

### ✅ Prerequisites (Already Completed)

- [x] Phase 1-5 complete (backend, frontend, testing)
- [x] Stripe products created (Pro, Pro Plus)
- [x] Stripe prices created (4 total: monthly/annual for each tier)
- [x] Stripe webhook endpoint configured
- [x] Price IDs copied to environment variables
- [x] Webhook secret obtained from Stripe
- [x] All code quality checks passing (TypeScript, ESLint, mypy, black)

### ⏳ To Complete in This Phase

- [ ] Configure Stripe Billing Portal
- [ ] Set business information in Stripe
- [ ] Prepare production environment variables
- [ ] Run database migration in production
- [ ] Deploy backend to production
- [ ] Deploy frontend to production
- [ ] Verify webhook connectivity
- [ ] Perform smoke tests
- [ ] Switch to production API keys (final step)

---

## Step 1: Configure Stripe Billing Portal

**Goal:** Configure the customer self-service portal for subscription management.

### Access Billing Portal Settings

1. Go to: https://dashboard.stripe.com/settings/billing/portal
2. Click **"Activate test link"** (for test mode first)

### Portal Configuration

#### A. Customer Information
- [x] **Allow customers to update email** - ✅ Enabled
- [x] **Allow customers to update billing address** - ✅ Enabled

#### B. Subscriptions
- [x] **Allow customers to cancel subscriptions** - ✅ Enabled
  - Cancel mode: **"At period end"** (recommended)
  - Also offer: **"Immediately"** (optional)
- [x] **Allow customers to switch plans** - ✅ Enabled
  - Proration behavior: **"Always invoice immediately"**
  - Available plans: Pro Monthly, Pro Annual, Pro Plus Monthly, Pro Plus Annual
- [x] **Allow customers to pause subscriptions** - ❌ Disabled (not needed)

#### C. Payment Methods
- [x] **Allow customers to update payment methods** - ✅ Enabled
- [x] **Allow customers to remove payment methods** - ❌ Disabled (require at least one)

#### D. Invoice History
- [x] **Show invoice history** - ✅ Enabled

#### E. Branding (Optional)
- [ ] **Upload logo** (recommended: 512x512px PNG)
- [ ] **Accent color** (use your brand color, e.g., `#7c3aed` for violet)
- [ ] **Business name** (e.g., "Gear Stack")
- [ ] **Support email** (e.g., `support@yourapp.com`)
- [ ] **Terms of Service URL** (e.g., `https://yourapp.com/terms`)
- [ ] **Privacy Policy URL** (e.g., `https://yourapp.com/privacy`)

### Test the Portal

```bash
# Generate test portal link
stripe billing_portals sessions create \
  --customer=cus_test... \
  --return_url=https://yourapp.com/billing
```

**Verification:**
- ✅ Portal loads correctly
- ✅ Can view subscription details
- ✅ Can update payment method
- ✅ Can cancel subscription (test mode)
- ✅ Can switch between plans

---

## Step 2: Set Business Information in Stripe

**Goal:** Configure your business details for invoices and customer communications.

### Business Details

1. Go to: https://dashboard.stripe.com/settings/public
2. Fill in:
   - **Business name:** Gear Stack (or your company name)
   - **Support email:** support@yourapp.com
   - **Support phone:** (optional)
   - **Business website:** https://yourapp.com

### Tax Settings (Optional)

1. Go to: https://dashboard.stripe.com/settings/tax
2. Configure tax collection if required in your jurisdiction

### Statement Descriptor

1. Go to: https://dashboard.stripe.com/settings/public
2. Set **Statement descriptor:** `GEARSTACK` (max 22 chars)
   - This appears on customer credit card statements

---

## Step 3: Prepare Production Environment Variables

**Goal:** Document all environment variables needed for production.

### Backend Environment Variables

Create a checklist of variables to set in production:

```bash
# ============================================
# Database
# ============================================
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# ============================================
# Security
# ============================================
SECRET_KEY=<generate-new-32-char-random-key>
ALLOWED_HOSTS=["yourdomain.com","www.yourdomain.com"]
ENVIRONMENT=production

# ============================================
# CORS
# ============================================
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# ============================================
# Stripe (Production Keys)
# ============================================
STRIPE_ENABLED=true
STRIPE_SECRET_KEY=sk_live_...  # ⚠️ USE TEST MODE FIRST: sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_live_...  # ⚠️ USE TEST MODE FIRST: pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...  # From production webhook endpoint

# Price IDs (same as test mode)
STRIPE_PRO_MONTHLY_PRICE_ID=price_...
STRIPE_PRO_ANNUAL_PRICE_ID=price_...
STRIPE_PRO_PLUS_MONTHLY_PRICE_ID=price_...
STRIPE_PRO_PLUS_ANNUAL_PRICE_ID=price_...

# ============================================
# Email (if configured)
# ============================================
# SMTP_HOST=smtp.yourprovider.com
# SMTP_PORT=587
# SMTP_USER=noreply@yourdomain.com
# SMTP_PASSWORD=<smtp-password>
# SMTP_FROM_EMAIL=noreply@yourdomain.com
```

### Frontend Environment Variables

```bash
# ============================================
# API Configuration
# ============================================
VITE_API_PROXY_URL=https://api.yourdomain.com

# ============================================
# Stripe (Production Keys)
# ============================================
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...  # ⚠️ USE TEST MODE FIRST

# Price IDs (same as test mode)
VITE_STRIPE_PRO_MONTHLY_PRICE_ID=price_...
VITE_STRIPE_PRO_ANNUAL_PRICE_ID=price_...
VITE_STRIPE_PRO_PLUS_MONTHLY_PRICE_ID=price_...
VITE_STRIPE_PRO_PLUS_ANNUAL_PRICE_ID=price_...
```

### Security Best Practices

- [ ] **Never commit** `.env` files to git
- [ ] **Use different keys** for test vs. production
- [ ] **Generate new SECRET_KEY** for production (32+ characters)
- [ ] **Rotate keys periodically** (every 90 days recommended)
- [ ] **Use secrets management** (e.g., AWS Secrets Manager, HashiCorp Vault)

---

## Step 4: Run Database Migration

**Goal:** Create billing tables and migrate existing premium users.

### Pre-Migration Backup

**CRITICAL:** Always backup your database before migration!

```bash
# PostgreSQL backup
pg_dump -h your-host -U your-user -d your-database > backup_before_billing_$(date +%Y%m%d_%H%M%S).sql

# Or via Docker
docker exec your-postgres-container pg_dump -U postgres your-database > backup_before_billing_$(date +%Y%m%d_%H%M%S).sql
```

### Run Migration

**Option 1: Via Docker (Recommended)**

```bash
# Access container
docker exec -it gear-stack-app bash

# Run migration
cd /app
python migrations/047_add_billing_tables.py upgrade
```

**Option 2: Direct Python**

```bash
cd backend
source .venv/bin/activate
python migrations/047_add_billing_tables.py upgrade
```

### Verify Migration

```sql
-- Check tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('subscriptions', 'stripe_webhook_events', 'subscription_history');

-- Check existing premium users were migrated
SELECT
    u.email,
    s.plan_tier,
    s.status,
    s.is_grandfathered
FROM users u
JOIN subscriptions s ON s.user_id = u.id
WHERE u.is_premium = true;

-- Should show all premium users with:
-- plan_tier = 'pro'
-- status = 'active'
-- is_grandfathered = true
```

### Rollback (If Needed)

```bash
# Only if migration fails
python migrations/047_add_billing_tables.py downgrade
```

---

## Step 5: Deploy Backend to Production

**Goal:** Deploy backend with billing module to production environment.

### Pre-Deployment Checks

```bash
# Run all quality checks
cd backend

# Type checking
python -m mypy app --config-file pyproject.toml

# Code formatting
python -m black --check .

# Run tests
python -m pytest tests/test_billing_service.py -v
```

### Deployment Steps

**Method depends on your infrastructure:**

#### Option A: Docker Deployment

```bash
# Build production image
docker build -t gear-stack-backend:billing-v1 -f backend/Dockerfile .

# Tag for registry
docker tag gear-stack-backend:billing-v1 your-registry.com/gear-stack-backend:billing-v1

# Push to registry
docker push your-registry.com/gear-stack-backend:billing-v1

# Deploy (depends on your orchestration)
# - Docker Compose: docker-compose -f docker-compose.prod.yml up -d
# - Kubernetes: kubectl apply -f k8s/backend-deployment.yaml
# - ECS/Fargate: Update task definition
```

#### Option B: Platform-as-a-Service (Heroku, Render, etc.)

```bash
# Example for Heroku
heroku container:push web -a your-app-name
heroku container:release web -a your-app-name
```

#### Option C: VM Deployment

```bash
# SSH to server
ssh user@your-server.com

# Pull latest code
cd /opt/gear-stack
git pull origin main

# Install dependencies
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart gear-stack-backend
```

### Post-Deployment Verification

```bash
# Check health endpoint
curl https://api.yourdomain.com/health

# Check billing endpoints (requires auth)
curl https://api.yourdomain.com/api/billing/subscription \
  -H "Authorization: Bearer <token>"

# Check logs
docker logs gear-stack-app --tail 100 -f
# or
journalctl -u gear-stack-backend -f
```

---

## Step 6: Deploy Frontend to Production

**Goal:** Deploy frontend with billing UI to production.

### Build for Production

```bash
cd /path/to/gear-stack

# Install dependencies
pnpm install

# Type check
pnpm type-check

# Lint
pnpm lint

# Build for production
pnpm build

# Preview build (optional)
pnpm preview
```

### Deployment Steps

**Method depends on your hosting:**

#### Option A: Static Hosting (Netlify, Vercel, Cloudflare Pages)

```bash
# Netlify
netlify deploy --prod --dir=dist

# Vercel
vercel --prod

# Cloudflare Pages (via git push)
git push origin main
```

#### Option B: CDN + Object Storage (S3, GCS, Azure Blob)

```bash
# AWS S3 + CloudFront
aws s3 sync dist/ s3://your-bucket-name/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"

# Google Cloud Storage
gsutil -m rsync -r -d dist/ gs://your-bucket-name/
```

#### Option C: Traditional Web Server

```bash
# Upload to server
rsync -avz dist/ user@your-server.com:/var/www/gear-stack/

# Restart web server
ssh user@your-server.com "sudo systemctl restart nginx"
```

### Post-Deployment Verification

```bash
# Check homepage loads
curl -I https://yourdomain.com

# Check billing page loads
curl -I https://yourdomain.com/billing

# Check JavaScript bundle
curl -I https://yourdomain.com/assets/index-*.js
```

**Manual Checks:**
- [ ] Open https://yourdomain.com in browser
- [ ] Navigate to /billing page
- [ ] Check console for errors (F12)
- [ ] Verify plan cards display correctly
- [ ] Check responsive design (mobile/tablet/desktop)

---

## Step 7: Verify Webhook Connectivity

**Goal:** Ensure Stripe can reach your production webhook endpoint.

### Update Webhook Endpoint in Stripe

1. Go to: https://dashboard.stripe.com/webhooks
2. Click on your webhook endpoint
3. Verify **Endpoint URL:** `https://api.yourdomain.com/api/billing/webhooks/stripe`
4. Verify **Events to send:**
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

### Test Webhook Connectivity

#### Method 1: Stripe Dashboard Test

1. Go to your webhook endpoint in Stripe Dashboard
2. Click **"Send test webhook"**
3. Select event: `customer.subscription.created`
4. Click **"Send test event"**

**Expected Result:**
- ✅ Status: 200 OK
- ✅ Response time: <500ms

#### Method 2: Trigger Real Event (Test Mode)

```bash
# Ensure using TEST API keys (sk_test_...)

# Create test checkout session
stripe checkout sessions create \
  --mode subscription \
  --success-url "https://yourdomain.com/billing/success" \
  --cancel-url "https://yourdomain.com/billing/cancel" \
  --line-items '[{"price": "price_test_...", "quantity": 1}]' \
  --customer-email "test@example.com"

# Complete checkout in browser
# Check webhook received in Stripe Dashboard
```

### Verify Webhook Processing

**Check database:**

```sql
-- Check webhook events table
SELECT
    stripe_event_id,
    event_type,
    processed,
    error_message,
    created_at
FROM stripe_webhook_events
ORDER BY created_at DESC
LIMIT 10;

-- Should show recent webhook events with processed=true
```

**Check backend logs:**

```bash
# Search for webhook processing logs
docker logs gear-stack-app | grep "webhook"

# Should see:
# "Received webhook event: evt_..."
# "Processing webhook event type: customer.subscription.created"
# "Webhook processed successfully"
```

---

## Step 8: Perform Smoke Tests

**Goal:** Verify all critical billing flows work in production.

### Test 1: Checkout Flow (Test Mode)

**⚠️ IMPORTANT:** Use test mode API keys first!

1. **Create test user account**
   - Register at https://yourdomain.com/auth/register
   - Verify email if required

2. **Navigate to billing page**
   - Go to https://yourdomain.com/billing
   - Should see FREE tier status

3. **Initiate checkout**
   - Click "Upgrade to Pro" (monthly or annual)
   - Should redirect to Stripe Checkout

4. **Complete test payment**
   - Use test card: `4242 4242 4242 4242`
   - Expiry: Any future date
   - CVC: Any 3 digits
   - Click "Subscribe"

5. **Verify success**
   - Should redirect to `/billing/success`
   - Should show "Subscription Activated!" message
   - Return to billing page
   - Should show Pro tier status

### Test 2: Billing Portal

1. **Access portal**
   - On billing page, click "Manage Subscription"
   - Should redirect to Stripe Billing Portal

2. **Verify portal features**
   - [ ] Can view subscription details
   - [ ] Can see payment method
   - [ ] Can update payment method
   - [ ] Can view invoice history
   - [ ] Can cancel subscription

3. **Test plan switch**
   - Switch from Pro to Pro Plus (or vice versa)
   - Verify new plan reflects in app

### Test 3: Cancellation Flow

**Use the comprehensive test guide:**
- See: `docs/testing/billing-cancellation-test-guide.md`

**Quick test:**
1. In Billing Portal, cancel subscription
2. Choose "Cancel at period end"
3. Return to app
4. Verify warning banner shows: "Subscription will cancel on [date]"

### Test 4: Grandfathered User

1. **Create test grandfathered user** (via admin panel or SQL):
   ```sql
   -- Set existing user as grandfathered
   UPDATE subscriptions
   SET is_grandfathered = true
   WHERE user_id = 'test_user_id';
   ```

2. **Verify UI:**
   - [ ] Crown icon shows on profile
   - [ ] "Lifetime Pro Access" badge displayed
   - [ ] Cannot cancel subscription
   - [ ] "Manage Billing" button disabled

### Test 5: Upgrade Prompts (FREE Users)

1. **Log in as FREE tier user**
2. **Navigate to dashboard**
3. **Verify:**
   - [ ] UpgradePromptBanner shows (violet gradient)
   - [ ] Can dismiss banner
   - [ ] Banner stays dismissed after page reload

### Test 6: Subscription Badge

1. **Navigate to profile page**
2. **Verify badge shows:**
   - FREE tier: Secondary badge, no icon
   - Pro tier: Default badge, Sparkles icon
   - Pro Plus: Premium badge, Sparkles icon
   - Grandfathered: Premium badge, Crown icon

---

## Step 9: Monitor Initial Usage

**Goal:** Monitor system health during first real subscriptions.

### Monitoring Checklist

**Webhook Events:**
```sql
-- Check webhook processing success rate
SELECT
    event_type,
    COUNT(*) as total,
    SUM(CASE WHEN processed = true THEN 1 ELSE 0 END) as processed,
    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as errors
FROM stripe_webhook_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY event_type;
```

**Subscription Metrics:**
```sql
-- Current subscription breakdown
SELECT
    plan_tier,
    status,
    COUNT(*) as count
FROM subscriptions
GROUP BY plan_tier, status;

-- Today's new subscriptions
SELECT COUNT(*) as new_subscriptions_today
FROM subscriptions
WHERE created_at >= CURRENT_DATE;
```

**Backend Logs:**
```bash
# Monitor for errors
docker logs gear-stack-app --tail 100 -f | grep -i error

# Monitor billing operations
docker logs gear-stack-app --tail 100 -f | grep -i billing
```

**Stripe Dashboard:**
- Monitor: https://dashboard.stripe.com/events
- Check for failed payments
- Review webhook delivery success rate

---

## Step 10: Switch to Production API Keys

**⚠️ CRITICAL:** Only do this after all tests pass!

### Pre-Switch Checklist

- [ ] All smoke tests passed in test mode
- [ ] Webhook connectivity verified
- [ ] Database migration successful
- [ ] No errors in logs
- [ ] Billing Portal configured
- [ ] Business information set

### Switch API Keys

**Backend:**
```bash
# Update environment variables
STRIPE_SECRET_KEY=sk_live_...  # Changed from sk_test_
STRIPE_PUBLISHABLE_KEY=pk_live_...  # Changed from pk_test_
STRIPE_WEBHOOK_SECRET=whsec_...  # Production webhook secret
```

**Frontend:**
```bash
# Update environment variables
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...  # Changed from pk_test_
```

**Restart services:**
```bash
# Backend
docker restart gear-stack-app

# Frontend (rebuild and redeploy)
pnpm build
# Deploy dist/ to production
```

### Verify Production Mode

```bash
# Check Stripe Dashboard shows live mode (toggle in top-left)
# Create real checkout session (will charge real money!)
```

---

## Step 11: Go Live! 🎉

**Goal:** Announce billing to users and monitor.

### Launch Checklist

- [ ] Production API keys active
- [ ] All systems operational
- [ ] Monitoring in place
- [ ] Support email configured
- [ ] Billing documentation ready for users

### Announce to Users

**Example announcement:**

> 🎉 **Introducing Gear Stack Pro & Pro Plus!**
>
> We're excited to announce new subscription plans with enhanced features:
>
> **Pro** ($5/mo or $50/yr):
> - AI-powered gear recommendations
> - $1 worth of AI tokens/month
> - 5GB storage
> - 10,000 items limit
>
> **Pro Plus** ($15/mo or $150/yr):
> - Everything in Pro
> - Priority AI processing
> - $10 worth of AI tokens/month
> - 50GB storage
> - 50,000 items limit
>
> 👉 [View Plans](/billing)
>
> **Note:** Existing premium users have been grandfathered into Pro with lifetime access. Thank you for your early support! 🙏

### First 24 Hours

**Monitor closely:**
- [ ] Check every hour for errors
- [ ] Respond to support emails promptly
- [ ] Monitor Stripe Dashboard for failed payments
- [ ] Watch webhook processing success rate
- [ ] Track conversion metrics

### Post-Launch Tasks

**Week 1:**
- Collect user feedback
- Monitor churn rate
- Track payment failures
- Optimize conversion funnel

**Week 2:**
- Review metrics and adjust pricing if needed
- Document any issues encountered
- Plan improvements based on feedback

---

## Rollback Procedures

### If Critical Issues Arise

**Option 1: Disable Stripe Integration**
```bash
# Backend .env
STRIPE_ENABLED=false
```

**Option 2: Rollback Database Migration**
```bash
python migrations/047_add_billing_tables.py downgrade
```

**Option 3: Revert Code Deployment**
```bash
# Deploy previous version
git checkout <previous-commit>
# Rebuild and deploy
```

---

## Success Criteria

✅ **Phase 6 Complete When:**

1. All smoke tests passed
2. Production webhook connectivity verified
3. Real checkout flow working
4. Billing Portal functional
5. Monitoring in place
6. First real subscription processed successfully
7. No critical errors in 24 hours
8. User announcement published

---

## Support & Resources

**Documentation:**
- [Stripe Dashboard](https://dashboard.stripe.com)
- [Stripe API Docs](https://stripe.com/docs/api)
- [Billing Portal Docs](https://stripe.com/docs/billing/subscriptions/integrating-customer-portal)
- [Webhook Guide](https://stripe.com/docs/webhooks)

**Internal Docs:**
- [Cancellation Test Guide](../testing/billing-cancellation-test-guide.md)
- [Performance Recommendations](../optimization/billing-performance-recommendations.md)
- [Phase 5 Summary](../plans/PHASE-5-COMPLETION-SUMMARY.md)

**Support:**
- Stripe Support: https://support.stripe.com
- Stripe Status: https://status.stripe.com

---

**Next:** Start with Step 1 (Configure Stripe Billing Portal) 🚀
