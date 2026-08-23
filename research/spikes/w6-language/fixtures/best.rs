//! Inventory helpers for the probe fixture.

/// Add `n` units of `sku`, refusing negative quantities.
pub fn restock(counts: &mut std::collections::HashMap<String, i64>, sku: &str, n: i64)
    -> Result<i64, String>
{
    if n < 0 {
        return Err("negative restock".to_string());
    }
    let e = counts.entry(sku.to_string()).or_insert(0);
    *e += n;
    Ok(*e)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adds_units() {
        let mut c = std::collections::HashMap::new();
        assert_eq!(restock(&mut c, "a", 2), Ok(2));
    }
}
