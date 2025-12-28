<template>
  <div class="relative min-h-screen px-6 py-12 lg:px-16 lg:py-20">
    <div
      class="mx-auto grid w-full max-w-6xl gap-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]"
    >
      <section class="fade-rise fade-delay-1 flex min-w-0 flex-col justify-center">
        <p class="text-xs uppercase tracking-[0.35em] text-slate">
          Blog Platform
        </p>
        <h1 class="mt-4 text-[clamp(2.25rem,4vw,3.4rem)] font-semibold text-ink">
          简洁而有力的内容体验
        </h1>
        <p class="mt-6 max-w-xl text-lg leading-relaxed text-slate">
          以清晰的视觉层次与轻盈的交互体验，建立可靠的写作与阅读空间。
        </p>
        <div class="mt-10 flex flex-wrap gap-4">
          <div class="rounded-2xl bg-white/80 px-5 py-4 shadow-soft">
            <p class="text-sm text-slate">沉浸式阅读</p>
            <p class="mt-2 text-lg font-semibold text-ink">柔和排版</p>
          </div>
          <div class="rounded-2xl bg-white/80 px-5 py-4 shadow-soft">
            <p class="text-sm text-slate">安全可靠</p>
            <p class="mt-2 text-lg font-semibold text-ink">专属账户</p>
          </div>
        </div>
      </section>

      <section
        class="fade-rise fade-delay-2 auth-card w-full max-w-[480px] justify-self-center rounded-3xl px-6 py-8 md:px-10 lg:justify-self-end"
      >
        <slot />
      </section>
    </div>
  </div>
</template>
