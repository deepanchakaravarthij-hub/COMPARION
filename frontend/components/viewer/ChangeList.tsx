"use client";

import type { ChangeCategory, ChangeItem, SemanticLabel, Severity } from "@/lib/types";
import { changeTone, sourceLabel } from "@/lib/viewer";

interface ChangeListProps {
  changes: ChangeItem[];
  activeChangeId: string | null;
  onActiveChange: (change: ChangeItem) => void;
  filters: {
    category: string;
    severity: string;
    semanticLabel: string;
    search: string;
  };
  onFiltersChange: (filters: ChangeListProps["filters"]) => void;
}

export function ChangeList({
  changes,
  activeChangeId,
  onActiveChange,
  filters,
  onFiltersChange
}: ChangeListProps) {
  const categories = unique(changes.map((change) => change.category));
  const severities = unique(changes.map((change) => change.severity));
  const semanticLabels = unique(changes.map((change) => change.semantic_label).filter(Boolean));
  const filteredChanges = changes.filter((change) => matchesFilters(change, filters));

  return (
    <aside className="panel">
      <div className="panel-header">
        <h3>Changes</h3>
        <p>
          {filteredChanges.length} of {changes.length} shown
        </p>
      </div>
      <div className="panel-body">
        <div className="filter-bar">
          <input
            className="input"
            onChange={(event) => onFiltersChange({ ...filters, search: event.target.value })}
            placeholder="Search changes"
            value={filters.search}
          />
          <select
            className="input"
            onChange={(event) => onFiltersChange({ ...filters, category: event.target.value })}
            value={filters.category}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <select
            className="input"
            onChange={(event) => onFiltersChange({ ...filters, severity: event.target.value })}
            value={filters.severity}
          >
            <option value="">All severities</option>
            {severities.map((severity) => (
              <option key={severity} value={severity}>
                {severity}
              </option>
            ))}
          </select>
          <select
            className="input"
            onChange={(event) => onFiltersChange({ ...filters, semanticLabel: event.target.value })}
            value={filters.semanticLabel}
          >
            <option value="">All semantic labels</option>
            {semanticLabels.map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="change-list">
          {filteredChanges.map((change) => (
            <button
              className={`change-card ${activeChangeId === change.id ? "active" : ""}`}
              key={change.id}
              onClick={() => onActiveChange(change)}
              type="button"
            >
              <div className="controls">
                <span className={`badge ${changeTone(change)}`}>{change.type}</span>
                <span className="badge">{change.category}</span>
                <span className="badge">{change.severity}</span>
              </div>
              <p>
                <strong>{change.id}</strong> {change.message}
              </p>
              <p className="muted">{sourceLabel(change.source_ref)}</p>
              {change.semantic_label ? (
                <span className="badge warning">
                  {change.semantic_label}
                  {typeof change.semantic_score === "number"
                    ? ` ${Math.round(change.semantic_score * 100)}%`
                    : ""}
                </span>
              ) : null}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}

function matchesFilters(change: ChangeItem, filters: ChangeListProps["filters"]) {
  if (filters.category && change.category !== filters.category) {
    return false;
  }
  if (filters.severity && change.severity !== filters.severity) {
    return false;
  }
  if (filters.semanticLabel && change.semantic_label !== filters.semanticLabel) {
    return false;
  }
  if (filters.search && !change.message.toLowerCase().includes(filters.search.toLowerCase())) {
    return false;
  }
  return true;
}

function unique<T extends ChangeCategory | Severity | SemanticLabel>(values: Array<T | undefined | null>) {
  return [...new Set(values.filter((value): value is T => Boolean(value)))];
}
