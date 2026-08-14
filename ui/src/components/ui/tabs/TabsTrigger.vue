<script setup lang="ts">
import { TabsTrigger, type TabsTriggerProps, useForwardProps } from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps<TabsTriggerProps & { class?: string }>();

const forwarded = useForwardProps(props);
</script>

<template>
  <TabsTrigger
    v-bind="forwarded"
    :class="
      cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm',
        props.class,
      )
    "
  >
    <slot />
  </TabsTrigger>
</template>
