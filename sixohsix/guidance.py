"""ASC 606 topics the agent can look up. Paraphrases only; paragraph numbers point to the codification."""

from typing import NamedTuple


class Note(NamedTuple):
    refs: tuple[str, ...]
    paraphrase: str


GUIDANCE: dict[str, Note] = {
    "contract_existence": Note(
        ("606-10-25-1", "606-10-25-2"),
        "A contract is in scope only when the parties have approved it, each party's rights and the payment terms "
        "can be identified, it has commercial substance, and collection of substantially all of the consideration "
        "is probable. Enforceability under law decides whether there is a contract, not its form.",
    ),
    "distinct": Note(
        ("606-10-25-19", "606-10-25-21", "606-10-25-22"),
        "A promised good or service is a separate performance obligation if the customer can benefit from it on its "
        "own or with readily available resources, and the promise is separately identifiable in the contract. It is "
        "not separately identifiable when the seller integrates it with other promises into a combined output, "
        "significantly modifies it, or the items are highly interdependent.",
    ),
    "series": Note(
        ("606-10-25-14", "606-10-25-15"),
        "A string of substantially the same distinct goods or services, each satisfied over time and measured the "
        "same way, is treated as one performance obligation. Stand-ready services such as support, hosting and "
        "when-and-if-available updates often qualify, so each period of service is a distinct increment.",
    ),
    "over_time_criteria": Note(
        ("606-10-25-27", "606-10-25-29"),
        "Revenue is recognized over time if the customer consumes the benefit as the seller performs, the seller's "
        "work creates or enhances an asset the customer controls, or the work has no alternative use and the seller "
        "has an enforceable right to payment for work done to date. If none of the three applies, the obligation is "
        "satisfied at a point in time.",
    ),
    "point_in_time": Note(
        ("606-10-25-30",),
        "For obligations satisfied at a point in time, revenue is recognized when control transfers. Indicators "
        "include a present right to payment, legal title, physical possession, transfer of the risks and rewards of "
        "ownership, and customer acceptance.",
    ),
    "hosting_vs_license": Note(
        ("985-20-15-5", "606-10-55-54"),
        "A software arrangement contains a license only if the customer may take possession of the software without "
        "significant penalty and can run it on its own hardware or through an unrelated host. Otherwise the customer "
        "is buying a hosted service, which is satisfied over time as access is provided.",
    ),
    "licenses_nature": Note(
        ("606-10-55-58", "606-10-55-59", "606-10-55-60", "606-10-55-62"),
        "Functional IP, such as software, media or a drug formula, has standalone utility, so a license to it is a "
        "right to use the IP as it exists and is recognized at a point in time. Symbolic IP, such as brands, logos "
        "and franchise rights, draws its value from the licensor's ongoing activities, so a license to it is a right "
        "to access the IP and is recognized over the license period.",
    ),
    "license_renewals": Note(
        ("606-10-55-58C",),
        "Revenue for a renewal or extension of a license cannot be recognized before the renewal period begins, even "
        "if the parties sign the renewal and the customer already has the software.",
    ),
    "royalty_exception": Note(
        ("606-10-55-65", "606-10-55-65A", "606-10-55-65B"),
        "A sales- or usage-based royalty promised for a license of IP is not estimated up front. It is recognized at "
        "the later of when the customer's sale or usage occurs and when the related obligation is satisfied. The "
        "exception applies when the license is the predominant item the royalty relates to, and does not apply to "
        "royalties on the sale of tangible goods or pure services.",
    ),
    "variable_consideration": Note(
        ("606-10-32-5", "606-10-32-6", "606-10-32-8"),
        "Discounts, rebates, refunds, credits, incentives, performance bonuses, penalties, and prices tied to usage "
        "or future events all make consideration variable. The seller estimates it using either the expected value "
        "or the most likely amount, whichever better predicts what it will be entitled to.",
    ),
    "constraint": Note(
        ("606-10-32-11", "606-10-32-12"),
        "Estimated variable consideration goes into the transaction price only to the extent that a significant "
        "reversal of recognized revenue is not probable once the uncertainty resolves. Factors that push toward "
        "constraining include outcomes outside the seller's influence, long resolution periods, and limited "
        "experience with similar contracts.",
    ),
    "material_right": Note(
        ("606-10-55-41", "606-10-55-42", "606-10-55-43"),
        "An option to buy more goods or services is a separate performance obligation only if it gives the customer "
        "a material right it would not get without entering the contract, such as a discount beyond the range "
        "normally given to that class of customer. Options at standalone selling price are marketing offers, not "
        "obligations.",
    ),
    "principal_agent": Note(
        ("606-10-55-36", "606-10-55-37A", "606-10-55-39"),
        "When another party is involved in delivering the good or service, the seller is a principal and reports "
        "gross revenue if it controls the item before transfer. Indicators of control include primary "
        "responsibility for fulfillment, inventory risk, and discretion over price. An agent reports only its fee "
        "or commission.",
    ),
    "modifications": Note(
        ("606-10-25-10", "606-10-25-12", "606-10-25-13"),
        "A change in scope or price is a separate contract if it adds distinct goods or services at their "
        "standalone selling prices. Otherwise it is accounted for prospectively when the remaining items are "
        "distinct from those already transferred, or with a cumulative catch-up adjustment when they are not.",
    ),
    "financing_component": Note(
        ("606-10-32-15", "606-10-32-16", "606-10-32-18"),
        "When payment timing gives either party a significant financing benefit, the transaction price is adjusted "
        "for the time value of money. As a practical expedient, no adjustment is needed when the gap between "
        "transfer and payment is expected to be one year or less.",
    ),
}
