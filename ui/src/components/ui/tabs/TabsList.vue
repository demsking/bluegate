<script setup lang="ts">
import { TabsList, type TabsListProps, useForwardProps } from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps<TabsListProps & { class?: string }>();

const forwarded = useForwardProps(props);
</script>

<template>
  <TabsList
    v-bind="forwarded"
    :class="
      cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
        props.class,
      )
    "
  >
    <slot />
  </TabsList>
</template>
