/** Inventory helpers for the probe fixture. */
export function restock(counts: Record<string, number>, sku: string, n: number): Record<string, number> {
  try {
    if (n < 0) { throw new Error("negative restock"); }
    counts[sku] = (counts[sku] ?? 0) + n;
  } catch (err) {
    throw new Error("bad counts");
  }
  return counts;
}

describe("restock", () => {
  test("adds units", () => {
    expect(restock({}, "a", 2)).toEqual({ a: 2 });
  });
});
