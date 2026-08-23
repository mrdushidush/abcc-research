/** Inventory helpers for the probe fixture. */
public final class Inventory {
    /** Add n units of sku, refusing negative quantities. */
    public static int restock(java.util.Map<String, Integer> counts, String sku, int n) {
        try {
            if (n < 0) { throw new IllegalArgumentException("negative restock"); }
            counts.merge(sku, n, Integer::sum);
        } catch (NullPointerException e) {
            throw new IllegalArgumentException("bad counts", e);
        }
        return counts.get(sku);
    }
}
