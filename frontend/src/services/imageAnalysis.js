export const AI_UNAVAILABLE =
  "Automatic image analysis is temporarily unavailable. Please select the observation type manually.";
export function aggregateImages(files) {
  if (!files.length || files.some((file) => !file.prediction)) return null;
  const counts = new Map();
  for (const { prediction } of files) {
    const row = counts.get(prediction.category) || { count: 0, total: 0 };
    row.count++;
    row.total += prediction.confidence;
    counts.set(prediction.category, row);
  }
  const ranked = [...counts.entries()].sort((a, b) => b[1].count - a[1].count);
  if (ranked[1]?.[1].count === ranked[0][1].count)
    return { category: "Other / Unclear", confidence: 0 };
  const [category, { count, total }] = ranked[0];
  return { category, confidence: total / count };
}
export function taskQueue(limit = 2) {
  let active = 0;
  const pending = [];
  function drain() {
    while (active < limit && pending.length) {
      const { task, resolve, reject } = pending.shift();
      active++;
      Promise.resolve()
        .then(task)
        .then(resolve, reject)
        .finally(() => {
          active--;
          drain();
        });
    }
  }
  return (task) =>
    new Promise((resolve, reject) => {
      pending.push({ task, resolve, reject });
      drain();
    });
}
