<script setup>
/**
 * Sign in: single sign-on first when it is set up (one button to the organisation's provider), a password form
 * under it while password sign-in is on. Errors from the provider come back as ?error= and are shown as they are.
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
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
    <main class="box">
      <div class="brand"><UiBrandMark :size="44" /><span>SIT-AIOPS</span></div>
      <h1>{{ t("Sign in", "เข้าสู่ระบบ") }}</h1>
      <p class="sub">{{ t("Use your organisation account, or the email and password an admin gave you.", "ใช้บัญชีขององค์กร หรืออีเมลและรหัสผ่านที่ผู้ดูแลให้ไว้") }}</p>

      <p v-if="error" class="err" role="alert">{{ error }}</p>

      <template v-if="providers">
        <UiButton v-if="providers.sso.enabled" block size="lg" href="/api/v1/auth/sso/start" icon="person">{{ providers.sso.label }}</UiButton>
        <div v-if="providers.sso.enabled && providers.password" class="or"><span>{{ t("or", "หรือ") }}</span></div>
        <form v-if="providers.password" class="form" @submit.prevent="submit">
          <UiField v-model="email" type="email" autocomplete="username" :label="t('Email', 'อีเมล')" placeholder="you@company.com" />
          <UiField v-model="password" type="password" autocomplete="current-password" :label="t('Password', 'รหัสผ่าน')" @enter="submit" />
          <UiButton type="submit" block size="lg" :variant="providers.sso.enabled ? 'tint' : 'primary'" :loading="busy" :disabled="!ready">
            {{ t("Sign in", "เข้าสู่ระบบ") }}</UiButton>
        </form>
        <p v-if="!providers.password && !providers.sso.enabled" class="sub">{{ t("Sign-in is not set up. Ask an admin.", "ยังไม่ได้ตั้งค่าการเข้าสู่ระบบ ติดต่อผู้ดูแล") }}</p>
      </template>
      <div v-else class="sk"><UiSkeleton h="44px" r="12px" /><UiSkeleton w="60%" /><UiSkeleton h="40px" r="10px" /></div>
    </main>
  </div>
</template>
<style scoped>
.login { min-height: 100vh; display: grid; place-items: center; padding: 24px 16px; background: var(--c-bg); }
.box { width: min(400px, 100%); background: var(--surface); border-radius: var(--radius-xl); box-shadow: var(--shadow-card); padding: 32px 28px; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: var(--fw-semibold); font-size: 18px; margin-bottom: 28px; }
h1 { font-size: 26px; font-weight: var(--fw-semibold); letter-spacing: -0.02em; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin: 6px 0 22px; }
.err { color: var(--c-bad-text); background: var(--c-bad-bg); border-radius: var(--radius-md); padding: 10px 12px; font-size: var(--fs-sm); margin-bottom: 16px; }
.or { display: flex; align-items: center; gap: 12px; color: var(--c-text-3); font-size: 12px; margin: 20px 0 4px; }
.or::before, .or::after { content: ""; flex: 1; height: 1px; background: var(--c-border); }
.form :deep(.ui-btn) { margin-top: 20px; }
.sk { display: flex; flex-direction: column; gap: 12px; }
</style>
