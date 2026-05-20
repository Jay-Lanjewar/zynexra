import { useCallback, useState, useMemo } from "react";
import type { RedactionEntity } from "./types";

export interface RedactionUIState {
  activeRedactions: Set<number>;
  entityGroups: Map<string, number[]>;
  entityCounts: Map<string, number>;
}

export function useRedactionState(entities: RedactionEntity[]) {
  const [activeRedactions, setActiveRedactions] = useState<Set<number>>(() => new Set(entities.map((_, idx) => idx)));

  const { entityGroups, entityCounts } = useMemo(() => {
    const groups = new Map<string, number[]>();
    const counts = new Map<string, number>();

    entities.forEach((entity, idx) => {
      if (!groups.has(entity.entity_type)) {
        groups.set(entity.entity_type, []);
      }
      groups.get(entity.entity_type)!.push(idx);

      counts.set(entity.entity_type, (counts.get(entity.entity_type) ?? 0) + 1);
    });

    return { entityGroups: groups, entityCounts: counts };
  }, [entities]);

  const toggleEntity = useCallback((entityIndex: number) => {
    setActiveRedactions((prev) => {
      const next = new Set(prev);
      if (next.has(entityIndex)) {
        next.delete(entityIndex);
      } else {
        next.add(entityIndex);
      }
      return next;
    });
  }, []);

  const toggleEntityType = useCallback(
    (entityType: string) => {
      const indices = entityGroups.get(entityType) ?? [];
      const allActive = indices.every((idx) => activeRedactions.has(idx));

      setActiveRedactions((prev) => {
        const next = new Set(prev);
        indices.forEach((idx) => {
          if (allActive) {
            next.delete(idx);
          } else {
            next.add(idx);
          }
        });
        return next;
      });
    },
    [activeRedactions, entityGroups]
  );

  const toggleAllRedactions = useCallback(() => {
    setActiveRedactions((prev) => {
      if (prev.size === entities.length) {
        return new Set();
      }
      return new Set(entities.map((_, idx) => idx));
    });
  }, [entities.length]);

  const isEntityActive = useCallback((entityIndex: number) => activeRedactions.has(entityIndex), [activeRedactions]);

  const getActiveCount = useCallback((): number => activeRedactions.size, [activeRedactions]);

  const getActiveCountByType = useCallback(
    (entityType: string): number => {
      const indices = entityGroups.get(entityType) ?? [];
      return indices.filter((idx) => activeRedactions.has(idx)).length;
    },
    [activeRedactions, entityGroups]
  );

  return {
    activeRedactions,
    entityGroups,
    entityCounts,
    toggleEntity,
    toggleEntityType,
    toggleAllRedactions,
    isEntityActive,
    getActiveCount,
    getActiveCountByType,
  };
}
