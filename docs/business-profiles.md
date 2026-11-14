# Business profiles

Default numbers for the simulation ([simulation.md](simulation.md)). They live in `backend/app/config.py` as `BUSINESS_PROFILES`, and every one is editable in the UI.

- Values marked **E** are our estimates (no good source found). The UI shows them with an "estimate" tag.
- Any other business type: the LLM fills the same fields, and every field is tagged **AI estimate**.
- Researched 2026-11-14. The sources are mostly industry blogs and POS/software vendors, not audited studies, so treat them as rules of thumb.

## Defaults

| Field | Boba / tea | Coffee shop | Fast-casual restaurant | Hair salon | Retail boutique |
|---|---|---|---|---|---|
| `typicalDailyCustomers` (calibration anchor) | 110 [1] | 200 [4] | 200 **E** | 25 [8] | 25 **E** (≈100 visitors × 25% conversion [12]) |
| `ticket` ± `ticketSd` ($) | 8.00 ± 1.25 [1][2] | 7.50 ± 1.50 [4][5] | 16 ± 3 [10] | 70 ± 15 [8][9] | 80 ± 20 [12] |
| `cogsMin`–`cogsMax` (% of revenue) | 25–35 [3][6] | 25–35 [4][5] | 26–32 [11] | 5–12 (products) [8] | 42–52 (gross margin 48–58%) [13] |
| `laborFixedMonthly` ($) | 7,000 | 14,400 | 28,800 | 3,000 (front desk) **E** | 7,000 **E** |
| `laborVariablePct` | 0 | 0 | 0 | 40% (commission) [8] | 0 |
| `otherFixedMonthly` ($) | 1,500 **E** | 1,500 **E** | 4,000 **E** | 1,500 **E** | 1,500 **E** |
| `daysOpen` / month | 30 | 30 | 30 | 26 [8] | 30 |
| `rampMin`–`rampMax` (months) | 3–9 **E** | 3–9 **E** | 3–9 **E** | 6–12 **E** | 4–10 **E** |
| `startupCost` ($, payback only) | 110,000 [3][7] | 150,000 **E** | 350,000 **E** | 90,000 [14] | 75,000 **E** |
| `radiusMi` | 1 | 1 | 1.5 | 3 | 3 |
| `lambda` (distance decay) | 2 | 2 | 2 | 1.5 | 1.5 [15] |
| `workerWeight` | 0.5 | 0.6 | 0.8 | 0.1 | 0.2 |
| `newCompetitorRatePerYear` (fallback) | 0.3 **E** | 0.3 **E** | 0.4 **E** | 0.3 **E** | 0.2 **E** |
| `rentShareMax` (rent ÷ revenue) | 15% | 15% | 10% | 15% [8] | 15% |
| Yelp categories | `bubbletea` | `coffee` | `hotdogs,sandwiches,burgers…` (by brief) | `hair` | by brief |

### How labor was set

Fixed labor = benchmark labor % × benchmark revenue, so the defaults agree with each other:

- **Boba:** 110 customers × $8 × 30 days ≈ $26.4k revenue × ~27% (range 25–32%) [3] ≈ **$7.0k**
- **Coffee:** 200 × $7.50 × 30 ≈ $45k × 32% (range 30–35%) [4][5] ≈ **$14.4k**
- **Fast casual:** 200 × $16 × 30 ≈ $96k × 30% (range 27–32%) [11] ≈ **$28.8k**
- **Salon:** mostly commission. 40% of revenue is variable (payroll 35–45%) [8], plus about $3k fixed for the front desk.

Sanity check: at these defaults a "typical" boba shop makes ~$26k/month, which is in line with ZenBusiness's $200–600k/year range for well-placed shops [2] and Menusifu's $32.8k/month at month 6 [1].

## Sources

1. Menusifu: [Bubble Tea Business Plan](https://www.menusifu.com/blog/bubble-tea-business-plan). 80–150 orders/day; $7–9 ticket.
2. ZenBusiness: [How to Start a Bubble Tea Shop](https://www.zenbusiness.com/start-a-business/food-service/bubble-tea-shop/). $7–12 ticket; $200–600k annual revenue.
3. Yen Chuan: [How to Start a Bubble Tea Business](https://store.yenchuan.co/blog/2026-guide-for-beginners/). COGS 20–30%, labor 25–32%; standard shop $75–150k.
4. Bellwether Coffee: [Coffee Shop Profit Margins](https://bellwethercoffee.com/blog/coffee-shop-profit-margins). $7–10+ ticket; COGS 25–35%; labor 25–32%.
5. BizMetricsHQ: [Coffee shop profitability](https://www.bizmetricshq.com/industries/restaurant-types/coffee-shop/). 200–500 customers/day; 180–250 to break even; $6–12 ticket.
6. Toast: [How Much Do Tea Shops Make](https://pos.toasttab.com/blog/on-the-line/how-much-do-tea-shops-make). COGS 30–40%.
7. Chowbus: [Bubble Tea Business Plan Guide](https://www.chowbus.com/blog/bubble-tea-business-plan). $75–150k startup.
8. BizMetricsHQ: [Hair salon](https://www.bizmetricshq.com/industries/beauty/hair-salon/), and Revenue Map: [How many customers does a hair salon need](https://revenuemap.app/questions/how-many-customers-does-a-hair-salon-need). $45–85 ticket; product 5–12%; payroll 35–50%; 16–25 customers/day to break even; 26 open days.
9. Lutily: [Salon weekly numbers](https://lutily.com/blog/salon-weekly-numbers-check). ~$70 average ticket.
10. Restaurant Bottom Line: [QSR vs Fast Casual vs Full Service](https://restaurantbottomline.com/2026/07/30/qsr-vs-fast-casual-vs-full-service-pl-comparison/). Fast casual $13–22 check.
11. FrillPick: [Food Cost vs Labor Cost](https://frillpick.com/benchmarks/food-cost-vs-labor-cost-restaurant/), and Zoomshift: [Restaurant operating costs](https://www.zoomshift.com/blog/restaurant-operating-costs-breakdown-what-you-should-be-spending-and-where-the-money-actually-goes/). Fast casual food 26–32%, labor 27–32%.
12. T-ROC: [Retail conversion rate](https://trocglobal.com/resources/definitions/what-is-retail-conversion-rate/), and ConversionXperts: [Retail Conversion Rate 2026](https://conversionxperts.com/the-retail-conversion-rate-guide-2026/). Boutique conversion 25–45%; $75–87 example tickets.
13. Nouz: [Retail store profitability](https://nouz.co/blog/retail-profitability-guide), and Eagle Rock CFO: [Gross margins in retail](https://www.eaglerockcfo.com/blog/profitability-guide/gross-margins-retail). Boutique gross margin 48–58%.
14. Vagaro: [Hair salon startup costs](https://www.vagaro.com/learn/hair-salon-startup-costs-full-breakdown), and Booksy: [Cost to open a hair salon](https://biz.booksy.com/blog/cost-to-open-a-hair-salon). Small salon $50–145k.
15. ArcGIS: [How the Huff model works](https://desktop.arcgis.com/en/arcmap/10.3/tools/business-analyst-toolbox/how-original-huff-model-works.htm), and MetricGate: [Huff calculator](https://metricgate.com/docs/huff-gravity-retail-location/). λ usually 1.5–2; 2+ for convenience, lower for destination.
