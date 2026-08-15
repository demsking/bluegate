<script setup lang="ts">
import { ChevronDown } from "@lucide/vue";
import {
  SelectTrigger,
  type SelectTriggerProps,
  useForwardProps,
} from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps<SelectTriggerProps & { class?: string }>();
const forwarded = useForwardProps(props);
</script>

<template>
  <SelectTrigger
    v-bind="forwarded"
    :class="
      cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
        props.class,
      )
    "
  >
    <slot />
    <ChevronDown class="h-4 w-4 opacity-50" />
  </SelectTrigger>
</template>
