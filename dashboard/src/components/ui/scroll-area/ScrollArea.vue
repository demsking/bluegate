<script setup lang="ts">
import {
  ScrollAreaRoot,
  ScrollAreaScrollbar,
  ScrollAreaThumb,
  ScrollAreaViewport,
  type ScrollAreaRootProps,
} from "reka-ui";
import { cn } from "@/lib/utils";

defineProps<ScrollAreaRootProps & { class?: string }>();
</script>

<template>
  <ScrollAreaRoot :class="cn('relative overflow-hidden', $props.class)">
    <ScrollAreaViewport class="h-full w-full rounded-[inherit]">
      <slot />
    </ScrollAreaViewport>
    <ScrollAreaScrollbar
      class="flex touch-none select-none bg-border p-0.5 transition-colors data-[orientation=vertical]:h-full data-[orientation=vertical]:w-2.5 data-[orientation=horizontal]:h-2.5 data-[orientation=horizontal]:flex-col"
      orientation="vertical"
    >
      <ScrollAreaThumb
        class="relative flex-1 rounded-full bg-muted-foreground/40"
      />
    </ScrollAreaScrollbar>
  </ScrollAreaRoot>
</template>
