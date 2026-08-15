<script setup lang="ts">
import {
  DialogOverlay,
  type DialogOverlayProps,
  useForwardProps,
} from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps<DialogOverlayProps & { class?: string }>();
const forwarded = useForwardProps(props);
</script>

<template>
  <DialogOverlay
    v-bind="forwarded"
    :class="
      cn(
        'fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out',
        props.class,
      )
    "
  />
</template>
