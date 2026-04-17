# Fejlesztői - penzugyi_naplo/ui/charts.py
# -----------------------------------------

"""
Diagramkezelő réteg (ChartManager) a Statisztika / Diagramok tabhoz
(penzugyi_naplo/ui/charts.py).

Felelősség:
    - havi, éves és számla-diagramok rajzolása
    - adatok lekérdezése a TransactionDatabase-ből
    - teljes frissítés: update_all()

Nem felelőssége:
    - UI elemek létrehozása (Figure / Canvas példányokat a MainWindow adja át)
    - layout vagy widget kezelés

Architektúra szerep:
    - a MainWindow-ból kiszervezett rajzolási logika
    - tiszta "rajzoló vezérlő" réteg a UI és DB között
"""


# --- Importok ---

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import numpy as np

# - Importok vége -


@dataclass
class ChartsContext:
    # Adatbázis referenciája (core.database.Database)
    db: object
    selected_year: int | None

    # matplotlib Figure + Canvas párok (a MainWindow hozza létre)
    fig_monthly: object
    canvas_monthly: object

    fig_annual: object
    canvas_annual: object

    fig_bills: object
    canvas_bills: object

    # Formázó callback (pl. MainWindow.format_number vagy core.utils.format_number_hu)
    format_number: callable


class ChartManager:
    def __init__(self, ctx: ChartsContext) -> None:
        self.ctx = ctx

    def update_context_year(self, year: int | None) -> None:
        self.ctx.selected_year = year

    def update_all(self) -> None:
        self.draw_monthly_comparison_chart()
        self.draw_annual_summary_chart()
        self.draw_bills_comparison_chart()

    # --- 1) Havi bevétel/kiadás oszlopdiagram ---
    def draw_monthly_comparison_chart(self) -> None:
        fig = self.ctx.fig_monthly
        canvas = self.ctx.canvas_monthly

        fig.clear()
        ax = fig.add_subplot(111)

        monthly_data = self.ctx.db.get_monthly_summary(self.ctx.selected_year)
        months = [item[0] for item in monthly_data]
        incomes = [item[1] for item in monthly_data]
        expenses = [abs(item[2]) for item in monthly_data]

        width = 0.35
        x = np.arange(len(months))

        # színeket direkt nem paraméterezzük most, marad a bevált
        ax.bar(x - width / 2, incomes, width, label="Bevétel", color="#4CAF50")
        ax.bar(x + width / 2, expenses, width, label="Kiadás", color="#F44336")

        ax.set_ylabel("Összeg (Ft)", fontsize=8)
        ax.set_title("Havi Összehasonlítás", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(axis="y", linestyle="--")

        fig.tight_layout()
        canvas.draw()

    # --- 2) Éves bevétel/kiadás kördiagram ---
    def draw_annual_summary_chart(self) -> None:
        fig = self.ctx.fig_annual
        canvas = self.ctx.canvas_annual

        fig.clear()
        ax = fig.add_subplot(111)

        annual_income, annual_expense = self.ctx.db.get_annual_totals(
            self.ctx.selected_year
        )

        data = [annual_income, annual_expense]
        labels = ["Összes Bevétel", "Összes Kiadás"]
        colors = ["#4CAF50", "#F44336"]

        if annual_income > 0 or annual_expense > 0:
            total = sum(data)

            def autopct_amount(pct: float) -> str:
                # pct: százalék, ebből visszaszámoljuk a Ft összeget
                amount = int(round(pct * total / 100.0))
                return self.ctx.format_number(str(amount)) + " Ft"

            ax.pie(
                data,
                labels=labels,
                autopct=autopct_amount,
                colors=colors,
                startangle=90,
                wedgeprops={"edgecolor": "black", "linewidth": 1},
            )
            ax.set_title("Teljes Éves Pénzforgalom", fontsize=10)
        else:
            ax.text(
                0.5,
                0.5,
                "Nincs elegendő adat az éves összegzéshez.",
                horizontalalignment="center",
                verticalalignment="center",
                transform=ax.transAxes,
            )

        fig.tight_layout()
        canvas.draw()

    # --- 3) Számlák: tervezett vs tényleges ---
    def draw_bills_comparison_chart(self) -> None:
        fig = self.ctx.fig_bills
        canvas = self.ctx.canvas_bills

        fig.clear()
        ax = fig.add_subplot(111)

        planned_expenses_json, _ = self.ctx.db.get_setting("planned_expenses_json")
        try:
            planned_dict = (
                json.loads(planned_expenses_json) if planned_expenses_json else {}
            )
        except (json.JSONDecodeError, TypeError):
            planned_dict = {}

        bill_txns = self.ctx.db.get_transactions_by_category_name(
            "Számlák (DOMINO, Vidanet, stb.)",
            self.ctx.selected_year,
        )

        actual_monthly_bills: dict[str, float] = {}
        for date, amount, _desc in bill_txns:
            month = str(date)[:7]  # YYYY-MM
            actual_monthly_bills[month] = actual_monthly_bills.get(month, 0) + abs(
                amount
            )

        current_month = datetime.now().strftime("%Y-%m")

        # utolsó 6 hónap megjelenítése (tényleges ∪ aktuális)
        months_to_show = sorted(
            list(set(actual_monthly_bills.keys()) | {current_month}), reverse=True
        )[:6]

        planned_amount = (
            sum(planned_dict.values()) if isinstance(planned_dict, dict) else 0
        )

        actuals = [actual_monthly_bills.get(m, 0) for m in months_to_show]
        planned = [planned_amount] * len(months_to_show)

        x = np.arange(len(months_to_show))
        width = 0.35

        ax.bar(
            x - width / 2,
            actuals,
            width,
            label="Tényleges Számlák (Havi)",
            color="#FFC107",
        )
        ax.bar(
            x + width / 2,
            planned,
            width,
            label="Tervezett Számlák (Összesen)",
            color="#673AB7",
        )

        ax.set_ylabel("Összeg (Ft)")
        ax.set_title("Tényleges vs. Tervezett Havi Számlakiadások")
        ax.set_xticks(x)
        ax.set_xticklabels(months_to_show, rotation=45, ha="right")
        ax.legend()
        ax.grid(axis="y", linestyle="--")

        fig.tight_layout()
        canvas.draw()
