<script setup lang="ts">
import { DialogPortal, type DialogPortalProps } from "reka-ui";

defineProps<DialogPortalProps>();
</script>

<template>
  <DialogPortal>
    <slot />
  </DialogPortal>
</template>
