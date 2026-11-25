<script setup>
/**
 * Sign in: single sign-on first when it is set up (one button to the organisation's provider), a password form
 * under it while password sign-in is on. Errors from the provider come back as ?error= and are shown as they are.
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { at } from "@/lib/base";
import { api } from "@/lib/api";
import { nextPath } from "@/lib/access";
import { useI18n } from "@/lib/i18n";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const { t } = useI18n();
const providers = ref(null);
const email = ref("");
const password = ref("");
const busy = ref(false);
const error = ref(route.query.error ? String(route.query.error) : "");
const ready = computed(() => email.value.trim() && password.value);
onMounted(async () => {
  try { providers.value = await api.auth.providers(); } catch { providers.value = { password: true, sso: { enabled: false } }; }
});
async function submit() {
  if (!ready.value) return;
  busy.value = true; error.value = "";
  try {
    await auth.login(email.value.trim(), password.value);
    router.replace(nextPath(route.query.next));
  } catch (e) {
    error.value = e.status === 429 ? t("Too many wrong passwords. Try again in a few minutes.", "ใส่รหัสผิดหลายครั้งเกินไป ลองใหม่อีกสักครู่")
      : e.status === 401 ? t("Email or password is not right.", "อีเมลหรือรหัสผ่านไม่ถูกต้อง") : e.message;
  } finally { busy.value = false; }
}
</script>
<template>
  <div class="login">
    <section class="login__shell" :aria-label="t('SIT-AIOPS sign in', 'เข้าสู่ระบบ SIT-AIOPS')">
      <aside class="welcome">
        <div class="welcome__brand">
          <span class="welcome__mark"><UiBrandMark :size="52" /></span>
          <span><small>{{ t("Welcome to", "ยินดีต้อนรับสู่") }}</small><strong>SIT-AIOPS</strong></span>
        </div>

        <div class="welcome__copy">
          <p class="welcome__eyebrow">{{ t("Operations intelligence", "ระบบอัจฉริยะสำหรับงานปฏิบัติการ") }}</p>
          <h2>{{ t("See the signal. Find the cause.", "เห็นสัญญาณ ค้นหาสาเหตุ") }}</h2>
          <p>{{ t("Metrics, traces, and logs come together in one investigation, while every fix stays under your approval.",
                  "รวม metric, trace และ log ไว้ในการสืบสวนเดียว โดยทุกการแก้ไขยังอยู่ภายใต้การอนุมัติของคุณ") }}</p>
        </div>

        <ul class="welcome__points" :aria-label="t('Platform capabilities', 'ความสามารถของระบบ')">
          <li>{{ t("Detect incidents", "ตรวจจับเหตุการณ์") }}</li>
          <li>{{ t("Investigate root causes", "สืบค้นสาเหตุหลัก") }}</li>
          <li>{{ t("Approve every fix", "อนุมัติทุกการแก้ไข") }}</li>
        </ul>
        <span class="welcome__wave" aria-hidden="true" />
      </aside>

      <main class="auth" aria-labelledby="login-title">
        <div class="auth__inner">
          <p class="auth__eyebrow">{{ t("Secure access", "การเข้าถึงที่ปลอดภัย") }}</p>
          <h1 id="login-title">{{ t("Sign in", "เข้าสู่ระบบ") }}</h1>
          <p class="auth__sub">{{ t("Use your organisation account, or the email and password an admin gave you.", "ใช้บัญชีขององค์กร หรืออีเมลและรหัสผ่านที่ผู้ดูแลให้ไว้") }}</p>

          <p v-if="error" class="err" role="alert">{{ error }}</p>

          <template v-if="providers">
            <UiButton v-if="providers.sso.enabled" block size="lg" :href="at('api/v1/auth/sso/start')" icon="person">{{ providers.sso.label }}</UiButton>
            <div v-if="providers.sso.enabled && providers.password" class="or"><span>{{ t("or", "หรือ") }}</span></div>
            <form v-if="providers.password" class="form" @submit.prevent="submit">
              <UiField v-model="email" type="email" autocomplete="username" :label="t('Email', 'อีเมล')" placeholder="you@company.com" />
              <UiField v-model="password" type="password" autocomplete="current-password" :label="t('Password', 'รหัสผ่าน')" @enter="submit" />
              <UiButton type="submit" block size="lg" :variant="providers.sso.enabled ? 'tint' : 'primary'" :loading="busy" :disabled="!ready">
                {{ t("Sign in", "เข้าสู่ระบบ") }}</UiButton>
            </form>
            <p v-if="!providers.password && !providers.sso.enabled" class="auth__sub auth__sub--empty">{{ t("Sign-in is not set up. Ask an admin.", "ยังไม่ได้ตั้งค่าการเข้าสู่ระบบ ติดต่อผู้ดูแล") }}</p>
          </template>
          <div v-else class="sk" aria-hidden="true"><UiSkeleton h="44px" r="12px" /><UiSkeleton w="60%" /><UiSkeleton h="40px" r="10px" /></div>
        </div>
      </main>
    </section>
  </div>
</template>
<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  overflow: auto;
  padding: clamp(var(--sp-4), 4vw, var(--sp-12));
  background:
    radial-gradient(70% 70% at 8% 10%, color-mix(in srgb, var(--c-primary) 10%, transparent), transparent 65%),
    radial-gradient(60% 60% at 92% 92%, color-mix(in srgb, var(--c-viz) 8%, transparent), transparent 70%),
    var(--c-bg);
}
.login__shell {
  width: min(980px, 100%);
  min-height: min(600px, calc(100vh - 48px));
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(380px, 0.92fr);
  overflow: hidden;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-xl);
  background: var(--c-surface);
  box-shadow: var(--shadow-2);
}
.welcome {
  position: relative;
  z-index: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: clamp(var(--sp-8), 5vw, 64px);
  padding-right: clamp(52px, 6vw, 76px);
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 82%, color-mix(in srgb, var(--c-primary) 32%, transparent), transparent 28%),
    radial-gradient(circle at 82% 12%, color-mix(in srgb, var(--c-viz) 23%, transparent), transparent 34%),
    linear-gradient(145deg, color-mix(in srgb, var(--c-primary) 28%, var(--c-raised)), var(--c-raised) 72%);
}
.welcome::before {
  content: "";
  position: absolute;
  right: -120px;
  bottom: -110px;
  width: 340px;
  aspect-ratio: 1;
  z-index: -1;
  border: 1px solid color-mix(in srgb, var(--c-text) 10%, transparent);
  border-radius: 50%;
  box-shadow:
    0 0 0 38px color-mix(in srgb, var(--c-text) 3%, transparent),
    0 0 0 76px color-mix(in srgb, var(--c-text) 2%, transparent);
}
.welcome__brand { display: flex; align-items: center; gap: var(--sp-3); }
.welcome__brand small,
.welcome__brand strong { display: block; }
.welcome__brand small { color: var(--c-text-2); font-size: var(--fs-xs); line-height: var(--lh-snug); }
.welcome__brand strong { margin-top: 2px; font-size: var(--fs-xl); letter-spacing: -0.02em; }
.welcome__mark {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--c-text) 10%, transparent);
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--c-surface) 68%, transparent);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--c-text) 9%, transparent);
}
.welcome__copy { max-width: 440px; margin: auto 0; padding: var(--sp-10) 0; }
.welcome__eyebrow,
.auth__eyebrow {
  margin: 0 0 var(--sp-3);
  color: var(--c-primary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.welcome h2 {
  max-width: 420px;
  margin: 0;
  font-size: clamp(32px, 4.2vw, 50px);
  line-height: 1.04;
  letter-spacing: -0.045em;
}
.welcome__copy > p:last-child {
  max-width: 410px;
  margin: var(--sp-5) 0 0;
  color: var(--c-text-2);
  font-size: var(--fs-lg);
  line-height: 1.65;
}
.welcome__points {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2) var(--sp-4);
  margin: 0;
  padding: 0;
  color: var(--c-text-2);
  font-size: var(--fs-xs);
  list-style: none;
}
.welcome__points li { display: flex; align-items: center; gap: var(--sp-2); }
.welcome__points li::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 15%, transparent);
}
.welcome__wave {
  position: absolute;
  inset-block: 0;
  right: -1px;
  width: 30px;
  background: radial-gradient(circle at 100% 15px, var(--c-surface) 14px, transparent 15px) 0 0 / 30px 30px repeat-y;
}
.auth {
  display: grid;
  min-width: 0;
  place-items: center;
  padding: clamp(var(--sp-8), 5vw, 64px);
  background: var(--c-surface);
}
.auth__inner { width: min(360px, 100%); }
.auth h1 {
  margin: 0;
  font-size: var(--fs-3xl);
  font-weight: var(--fw-semibold);
  letter-spacing: -0.035em;
}
.auth__sub {
  margin: var(--sp-2) 0 var(--sp-6);
  color: var(--c-text-3);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.auth__sub--empty { margin-top: var(--sp-6); }
.err { color: var(--c-bad-text); background: var(--c-bad-bg); border: 1px solid color-mix(in srgb, var(--c-bad) 34%, transparent); border-radius: var(--radius-md); padding: 10px 12px; font-size: var(--fs-sm); margin-bottom: var(--sp-4); }
.or { display: flex; align-items: center; gap: var(--sp-3); color: var(--c-text-3); font-size: var(--fs-xs); margin: var(--sp-5) 0 var(--sp-1); }
.or::before, .or::after { content: ""; flex: 1; height: 1px; background: var(--c-border); }
.form :deep(.ui-field input) { min-height: 44px; }
.form :deep(.ui-btn) { margin-top: var(--sp-5); }
.sk { display: flex; flex-direction: column; gap: var(--sp-3); }

@media (max-width: 760px) {
  .login { place-items: start center; padding: var(--sp-4); }
  .login__shell { min-height: calc(100vh - 32px); grid-template-columns: 1fr; }
  .welcome { min-height: 250px; padding: var(--sp-6); }
  .welcome__copy { margin: var(--sp-8) 0 var(--sp-6); padding: 0; }
  .welcome h2 { max-width: 320px; font-size: clamp(30px, 10vw, 40px); }
  .welcome__copy > p:last-child { max-width: 520px; margin-top: var(--sp-3); font-size: var(--fs-md); }
  .welcome__wave { display: none; }
  .auth { padding: var(--sp-8) var(--sp-6) var(--sp-10); }
}
@media (max-width: 420px) {
  .login { padding: 0; }
  .login__shell { min-height: 100vh; border: 0; border-radius: 0; }
  .welcome { min-height: 224px; padding: var(--sp-5); }
  .welcome__mark { width: 56px; height: 56px; }
  .welcome__copy { margin: var(--sp-7) 0 var(--sp-5); }
  .welcome__copy > p:last-child { display: none; }
  .welcome__points { gap: var(--sp-2) var(--sp-3); }
  .auth { padding: var(--sp-8) var(--sp-5) var(--sp-10); }
}
@media (max-height: 700px) and (min-width: 761px) {
  .login__shell { min-height: calc(100vh - 32px); }
  .welcome, .auth { padding-block: var(--sp-8); }
  .welcome__copy { padding-block: var(--sp-6); }
}
@media (prefers-reduced-motion: reduce) {
  .login *, .login *::before, .login *::after { scroll-behavior: auto; }
}
</style>
