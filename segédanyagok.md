 ### - Segédanyagok:
 # ------------------------

 ## Cél: Megtudd a miérteket, lásd az összefüggéseket
 ## - segít tanulni



# --- Statisztika ---
# Itt az oldal létrehozása és regisztrálása egy sorban történik.
#
# A StatisticsPage(...) létrehoz egy új oldal-példányt,
# az add_page(...) pedig rögtön beregisztrálja "statistics" kulccsal.
window.add_page("statistics", StatisticsPage(window.ctx, parent=window))


# --- Számlák ---
# Itt több sorra van szükség, mert a BillsPage példányt külön el kell érnünk.
#
# Miért?
# Mert a billRequested signal-t be kell kötni:
# window.bills_page.billRequested.connect(...)
#
# Ezért előbb létrehozzuk és eltároljuk window.bills_page néven,
# majd utána regisztráljuk.
window.bills_page = BillsPage(window, db=window.db)
window.bills_page.billRequested.connect(window.on_bill_requested)
window.add_page("bills", window.bills_page)


# --- Pénztárcák ---
# Itt is külön létrehozzuk az oldalt.
#
# A hibás próbálkozás ez volt:
# window.add_page("accounts", window.accounts_page)
#
# Ez azért hibás, mert a window.accounts_page még nem létezett.
#
# Előbb létre kell hozni:
window.accounts_page = AccountsPage(window, db=window.db)

# Utána már beregisztrálható "accounts" kulccsal:
window.add_page("accounts", window.accounts_page)





### Tanulság:

Az add_page() második paramétere mindig egy kész oldal-példány.

Ez lehet közvetlenül létrehozva:

    window.add_page("statistics", StatisticsPage(...))

vagy előbb eltárolva:

    window.accounts_page = AccountsPage(...)
    window.add_page("accounts", window.accounts_page)

A két forma ugyanazt az alapelvet használja.
A különbség csak az, hogy a több soros változatnál később is könnyen elérjük az oldalt.