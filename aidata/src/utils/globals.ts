export type StateColorKey = 
  | "deferred" | "failed" | "queued" | "removed" 
  | "restarting" | "running" | "scheduled" | "skipped"
  | "success" | "up_for_reschedule" | "up_for_retry" 
  | "upstream_failed";

const stateColors: Record<StateColorKey, string> = {
    "deferred": "mediumpurple",
    "failed": "red",
    "queued": "gray",
    "removed": "lightgrey",
    "restarting": "violet",
    "running": "lime",
    "scheduled": "tan",
    "skipped": "hotpink",
    "success": "green",
    "up_for_reschedule": "turquoise",
    "up_for_retry": "gold",
    "upstream_failed": "orange"
};
const autoRefreshInterval = 3;
const defaultDagRunDisplayNumber = 25;
const filtersOptions = {
    "taskStates": [
        "removed",
        "scheduled",
        "queued",
        "running",
        "success",
        "restarting",
        "failed",
        "up_for_retry",
        "up_for_reschedule",
        "upstream_failed",
        "skipped",
        "deferred"
    ],
    "dagStates": [
        "queued",
        "success",
        "running",
        "failed"
    ],
    "runTypes": [
        "backfill",
        "scheduled",
        "manual",
        "asset_triggered"
    ],
    "numRuns": [5, 25, 50, 100, 365]
};

export {
    stateColors,
    autoRefreshInterval,
    defaultDagRunDisplayNumber,
    filtersOptions,
};