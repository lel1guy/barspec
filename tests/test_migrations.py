"""Migration integrity: upgrading a real v0 database must preserve every row
and every cent, and dedupe stock correctly."""
import sqlite3

import db


def _conn(db):
    return sqlite3.connect(db)


class TestLegacyUpgrade:
    def test_version_bumped(self, legacy_db):
        conn = _conn(legacy_db.DB_PATH)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 12
        conn.close()

    def test_ingredients_table_gone(self, legacy_db):
        conn = _conn(legacy_db.DB_PATH)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingredients'"
        ).fetchall()
        assert rows == []
        conn.close()

    def test_stock_deduped_case_insensitive(self, legacy_db):
        conn = _conn(legacy_db.DB_PATH)
        # gin, campari, vermouth, prosecco -> 4 bottles; campari+campari = 1
        rows = conn.execute("SELECT name FROM stock_items ORDER BY name").fetchall()
        names = [r[0] for r in rows]
        assert len(names) == 4
        assert "Campari" in names and "campari" not in names
        conn.close()

    def test_lines_preserved_1_to_1(self, legacy_db):
        conn = _conn(legacy_db.DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM spec_lines").fetchone()[0]
        assert n == 5  # 3 + 2 original ingredient rows
        conn.close()

    def test_spec_columns_added(self, legacy_db):
        conn = _conn(legacy_db.DB_PATH)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(specs)").fetchall()]
        assert "price_eur" in cols and "target_gp" in cols
        conn.close()

    def test_stock_take_schema_added(self, legacy_db):
        """002 adds par_level + the two snapshot tables on top of 001."""
        conn = _conn(legacy_db.DB_PATH)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(stock_items)").fetchall()]
        assert "par_level" in cols
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert {"stock_takes", "stock_take_lines"} <= tables
        conn.close()

    def test_units_schema_added(self, legacy_db):
        """003 adds dimension on stock + unit on spec lines."""
        conn = _conn(legacy_db.DB_PATH)
        stock_cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(stock_items)").fetchall()]
        line_cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(spec_lines)").fetchall()]
        assert "dimension" in stock_cols
        assert "unit" in line_cols
        # legacy rows backfill as volume/ml — zero data rewrite
        dims = conn.execute(
            "SELECT DISTINCT dimension FROM stock_items").fetchall()
        units = conn.execute(
            "SELECT DISTINCT unit FROM spec_lines").fetchall()
        assert dims == [("volume",)]
        assert units == [("ml",)]
        conn.close()

    def test_cost_unchanged_after_upgrade(self, legacy_db):
        """Negroni cost must equal the old formula on the same numbers."""
        spec = legacy_db.get_spec(1)
        expected = 30 * 22.0 / 700 + 30 * 19.0 / 700 + 30 * 11.0 / 750
        assert spec["summary"]["cost_eur"] == round(expected, 3)

    def test_dedup_row_kept_the_priced_bottle(self, legacy_db):
        """The lowercase unpriced 'campari' must not shadow the priced one."""
        item = legacy_db.get_stock_item_by_name("Campari")
        assert item["bottle_price_eur"] == 19.0

    def test_upgrade_is_idempotent(self, legacy_db):
        """Running init_db twice never double-applies or reseeds."""
        legacy_db.init_db()
        conn = _conn(legacy_db.DB_PATH)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 12
        assert conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM stock_items").fetchone()[0] == 4
        conn.close()


class TestFreshInstall:
    def test_seed_through_new_schema(self, fresh_db):
        # 5 seed specs -> 15 unique bottles, 15 spec lines, 5 specs
        items = db_all(fresh_db, "SELECT COUNT(*) FROM stock_items")
        lines = db_all(fresh_db, "SELECT COUNT(*) FROM spec_lines")
        specs = db_all(fresh_db, "SELECT COUNT(*) FROM specs")
        assert (items, lines, specs) == (15, 15, 5)

    def test_seed_prices_present(self, fresh_db):
        conn = _conn(fresh_db)
        row = conn.execute(
            "SELECT price_eur, target_gp FROM specs WHERE name='Negroni'").fetchone()
        assert row[0] == 9.0 and row[1] == 75
        conn.close()

    def test_reinit_never_reseeds(self, fresh_db):
        db.init_db()
        assert db_all(fresh_db, "SELECT COUNT(*) FROM specs") == 5

    def test_reinit_never_resurrects_legacy_table(self, fresh_db):
        """init_db on an already-migrated DB must NOT recreate `ingredients`
        (the base schema is v0-only; migration 001 drops the table)."""
        def has_ingredients():
            conn = _conn(fresh_db)
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ingredients'"
            ).fetchall()
            conn.close()
            return len(rows) > 0

        assert not has_ingredients()          # fresh init went through 001 -> dropped
        db.init_db()                          # second init must not resurrect it
        assert not has_ingredients()


def db_all(db_path, sql):
    conn = _conn(db_path)
    v = conn.execute(sql).fetchone()[0]
    conn.close()
    return v
