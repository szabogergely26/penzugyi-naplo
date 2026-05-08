"""
penzugyi_naplo/ui/main_window/likviditas/import_handlers.py

Likviditás nézethez tartozó import műveletek.

Felelősség:
- ODS import varázsló megnyitása
- importálható tranzakciók lekérése
- import megerősítésének kezelése
- importált tranzakciók adatbázisba mentése
- import utáni évfülek és oldalak frissítése

Fontos:
- ez UI-szintű handler
- az import feldolgozás részletei továbbra is az importer/wizard modulokban vannak
- a MainWindow csak meghívja ezt a handlert
"""

from PySide6.QtWidgets import QDialog, QMessageBox

from penzugyi_naplo.ui.importers.ods_transaction_import_wizard import (
    OdsTransactionImportWizard,
)


def handle_ods_import(window) -> None:
    """
    ODS tranzakció import indítása.

    Lépések:
    - import varázsló megnyitása
    - importálható tranzakciók lekérése
    - konzolos előnézet kiírása
    - felhasználói megerősítés
    - adatbázisba mentés
    - UI frissítése
    """
    dialog = OdsTransactionImportWizard(window)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    transactions = dialog.get_importable_transactions()

    if not transactions:
        QMessageBox.information(
            window,
            "Import",
            "Nincs importálható tranzakció.",
        )
        return

    _print_import_preview(transactions)

    QMessageBox.information(
        window,
        "ODS import előnézet",
        "Az import előnézet elkészült.\n\n"
        f"Importálható tranzakciók száma: {len(transactions)}\n\n"
        "Az első néhány tranzakció kiíródott a konzolra.\n"
        "Adatbázisba mentés még nem történt.",
    )

    if not _confirm_import(window, len(transactions)):
        return

    saved_count, failed_count = _save_imported_transactions(window, transactions)

    QMessageBox.information(
        window,
        "Import kész",
        f"Sikeresen importált tranzakciók: {saved_count}\n"
        f"Hibás / kihagyott tranzakciók: {failed_count}",
    )

    _refresh_after_import(window)


def _print_import_preview(transactions) -> None:
    """Az első néhány importálható tranzakció kiírása konzolra."""

    print("ODS import - importálható tranzakciók:")
    print(f"Darabszám: {len(transactions)}")

    for tx in transactions[:10]:
        print(
            tx.tx_date,
            tx.tx_type,
            tx.category,
            tx.amount,
            tx.description,
        )


def _confirm_import(window, transaction_count: int) -> bool:
    """Import megerősítésének bekérése a felhasználótól."""

    answer = QMessageBox.question(
        window,
        "Import megerősítése",
        f"{transaction_count} tranzakció importálható.\n\n"
        "Biztosan beírod ezeket az adatbázisba?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    return answer == QMessageBox.StandardButton.Yes


def _save_imported_transactions(window, transactions) -> tuple[int, int]:
    """
    Importált tranzakciók mentése az adatbázisba.

    Megjegyzés:
    A category_id jelenleg ideiglenes egyszerűsítés:
    - income -> 2
    - egyéb -> 7
    """

    saved_count = 0
    failed_count = 0

    for tx in transactions:
        try:
            category_id = 2 if tx.tx_type == "income" else 7

            window.ctx.db.save_transaction(
                {
                    "date": tx.tx_date,
                    "type": tx.tx_type,
                    "amount": tx.amount,
                    "category_id": category_id,
                    "name": tx.description or "",
                    "description": tx.description or "",
                    "payment_source": "bank",
                }
            )

            saved_count += 1

        except Exception as exc:
            failed_count += 1
            print(f"Import hiba, forrás sor {tx.source_row}: {exc}")

    return saved_count, failed_count


def _refresh_after_import(window) -> None:
    """Évfülek és oldalak frissítése sikeres import után."""

    years = window.db.get_transaction_years()

    if years:
        window.year_tabs.set_years(years)

    if window.state.active_year in years:
        window.year_tabs.set_active_year(window.state.active_year, emit=False)
    else:
        window.state.active_year = years[0]
        window.year_tabs.set_active_year(years[0], emit=False)
        window.set_active_year(years[0])

    window.reload_all_pages()