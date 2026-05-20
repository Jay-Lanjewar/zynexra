import type { RedactionEntity } from "./types";

export interface EntityStats {
  total: number;
  active: number;
  byType: Map<string, { total: number; active: number }>;
}

export function computeEntityStats(entities: RedactionEntity[], activeIndices: Set<number>): EntityStats {
  const byType = new Map<string, { total: number; active: number }>();

  entities.forEach((entity, idx) => {
    const type = entity.entity_type;
    if (!byType.has(type)) {
      byType.set(type, { total: 0, active: 0 });
    }
    const stats = byType.get(type)!;
    stats.total += 1;
    if (activeIndices.has(idx)) {
      stats.active += 1;
    }
  });

  return {
    total: entities.length,
    active: activeIndices.size,
    byType,
  };
}

export function computeLivePreview(originalText: string, entities: RedactionEntity[], activeIndices: Set<number>): string {
  const activeEntities = entities
    .map((entity, idx) => ({ ...entity, idx }))
    .filter((e) => activeIndices.has(e.idx))
    .sort((a, b) => b.start - a.start);

  let redacted = originalText;
  for (const entity of activeEntities) {
    redacted = redacted.slice(0, entity.start) + entity.replacement + redacted.slice(entity.end);
  }
  return redacted;
}

export function groupEntitiesByType(entities: RedactionEntity[]): Map<string, RedactionEntity[]> {
  const grouped = new Map<string, RedactionEntity[]>();
  entities.forEach((entity) => {
    if (!grouped.has(entity.entity_type)) {
      grouped.set(entity.entity_type, []);
    }
    grouped.get(entity.entity_type)!.push(entity);
  });
  return grouped;
}

export function sortEntityTypes(types: string[]): string[] {
  const priority: Record<string, number> = {
    PERSON: 0,
    EMAIL: 1,
    PHONE: 2,
    ADDRESS: 3,
    COMPANY: 4,
    LOCATION: 5,
    MONEY: 6,
    DATE: 7,
    ID_NUMBER: 8,
  };
  return types.sort((a, b) => (priority[a] ?? 99) - (priority[b] ?? 99));
}
