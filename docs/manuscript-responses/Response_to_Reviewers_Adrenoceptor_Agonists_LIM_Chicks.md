# Response to Reviewers

**Manuscript:** Subtype-Specific Efficacy of Adrenoceptor Agonists in Inhibiting Lens-Induced Myopia in Chicks  
**Uddin et al.**

Below are point-by-point responses. Suggested manuscript revisions are indicated where relevant. Pharmacological constants are taken from peer-reviewed binding/functional assays (human recombinant receptors unless noted) and should be interpreted cautiously for chick ocular tissue.

---

## Comment 1

> To be able to compare and discuss distinct effects of the drugs on the various adrenergic receptors, the manuscript should include information on the binding affinity and dose-effects of the agonists to their receptors (KD and/or EC50), as well as, if available, information on nonspecific binding of the drugs to other receptor classes.

### Answer

We agree and thank the reviewer. The original manuscript did not provide receptor affinity/potency data needed for subtype comparison. We will add a pharmacology summary (Introduction and/or Discussion, with a new table) based on published values:

**Lofexidine (α2-preferring agonist)**  
- High affinity/agonism at α2A and α2C: Ki ≈ 7.2 nM (α2A) and ≈ 12 nM (α2C); EC50 ≈ 4.9 nM (α2A) and ≈ 0.9 nM (α2C) (FDA prescribing information / in vitro binding).  
- Rat brain membrane Kd ≈ 5.5 nM at α2 sites.  
- Off-target / additional targets: imidazoline I1 (Ki ≈ 1.9 nM); agonist activity also reported at dopamine D2S and serotonin 5-HT1A/5-HT1B; some α1A affinity/agonism relative to clonidine (Gish et al., *Pharmacology & Pharmacy*, 2019).

**Metaraminol (α1-preferring; also indirect sympathomimetic)**  
- Human α1A whole-cell binding: log KD ≈ −7.21 (KD ≈ 62 nM); weaker at α1B/α1D (log KD roughly −5.8 to −7.0 depending on assay) (Proudman et al., *Pharmacol Res Perspect*, 2021).  
- Human α2A binding: log KD ≈ −5.50 (KD ≈ 3.2 µM) (Proudman et al., *Pharmacol Res Perspect*, 2022) → ~50-fold lower affinity at α2A than at α1A under matched methods.  
- Additional actions: mild β-activity; major clinical pressor effect partly via displacement/release of noradrenaline (indirect pathway), not only direct α1 agonism.

**Cirazoline**  
- Potent α1 agonist: Ki ≈ 120 nM (α1A), 960 nM (α1B), 660 nM (α1D); EC50 ≈ 71 / 79 / 240 nM at α1A / α1B / α1D (full agonist at α1A; partial at α1B/α1D).  
- Importantly, cirazoline is an **α2 antagonist** (pA2 ≈ 7.56; KB ≈ 28 nM), not a dual α1/α2 agonist (Ruffolo & Waddell, *J Pharmacol Exp Ther*, 1982). It also has weak antimuscarinic activity at high concentrations and binds imidazoline sites.

**Implication for our dose series (3 / 30 / 300 nmol in 10 µL):** assuming rapid mixing into ~150 µL liquid vitreous (common chick estimate), nominal peak vitreous concentrations are ~20 µM, ~200 µM, and ~2 mM. All three agents are therefore expected to occupy their primary targets at medium/high doses; selectivity windows may erode at 300 nmol, so off-target contributions (metaraminol→α2; lofexidine→α1/D2/5-HT; cirazoline→α2 antagonism) must be discussed explicitly.

We will also correct the manuscript’s description of cirazoline from “dual α1/α2-AR agonist” to “α1 agonist / α2 antagonist (imidazoline),” consistent with Ruffolo & Waddell (1982) and our own Discussion text that already notes α2 antagonism.

---

## Comment 2

> If I am correctly informed, metaraminol can also bind to the alpha-2a adrenergic receptor (however, depending on the test system, a 10- to 1,000-fold higher concentration is required to achieve 50% of the receptor effect). Could the effect of the α1 agonist also be due to its binding to the α2 receptor?

### Answer

Yes — metaraminol can bind α2A, and an α2 contribution cannot be excluded at higher doses.

Proudman et al. (2021–2022) report roughly **~50-fold preferential affinity for α1A over α2A** (KD ≈ 62 nM vs ≈ 3.2 µM). That fits the reviewer’s “10- to 1,000-fold” range and is assay-dependent.

In our LIM data, metaraminol was **ineffective at 3 nmol** but strongly effective at 30–300 nmol, whereas lofexidine was already effective at 3 nmol. That pattern is consistent with:
1. Primary action via α1 (and/or indirect NE release) requiring higher local concentration; and/or  
2. Progressive α2 engagement as vitreous concentration rises into the micromolar range.

We therefore will state in the Discussion that metaraminol’s medium/high-dose efficacy **may partly reflect α2A (or other off-target) occupancy**, and that subtype-selective antagonists (e.g., prazosin vs yohimbine/atipamezole co-administration) or more selective α1 tool compounds (e.g., A61603) are needed to isolate α1-specific contributions. Pure α1 mediation should not be claimed from the present agonist-only design.

---

## Comment 3

> It has to be made clearer, why agonists were studied instead of antagonists? Since antagonists increase tyrosine kinase activity and agonists decrease dopamine release (see below), one would expect an antagonist to have an inhibitory effect, or?

### Answer

We thank the reviewer for raising this important mechanistic point. We will clarify the rationale as follows.

**1. Empirical precedent in chick myopia favors agonists, not antagonists.**  
Carr, Nguyen & Stell (*Clin Exp Optom*, 2019) showed that α2 agonists (brimonidine, clonidine, guanfacine) inhibit form-deprivation myopia (FDM) in chicks, whereas the α2 antagonist **yohimbine alone did not inhibit FDM**. Thus, for the ocular-growth endpoint, antagonist → “more dopamine → less myopia” is **not** supported in vivo.

**2. The Iuvone & Rauch (1983) TH data do not map simply onto myopia control.**  
In rat retina, α2 antagonists (yohimbine, piperoxane) raise tyrosine hydroxylase (TH) activity in darkness, and the agonist clonidine can reduce TH activity under light. Higher TH/dopamine is generally a “stop” signal for axial elongation. That biochemical logic predicts antagonists should be anti-myopic — but Carr’s FDM results show the opposite pattern for growth. Possible reasons include species differences (rat vs chick), dark vs light adaptation state, pre- vs postsynaptic α2 loci, compensatory network effects, and the fact that TH activity ≠ sustained dopaminergic “stop” signaling during chronic LIM/FDM.

**3. Why we prioritized agonists.**  
- Prior myopia studies (chick FDM; guinea-pig/brimonidine work) used agonists successfully.  
- Clinical α2 agonists (brimonidine, clonidine class) are already ocular drugs, making agonist profiling translationally relevant.  
- Our goal was **subtype comparison among α1-, α2-preferring, and mixed tools** under LIM, which had not been done systematically.  
- Cirazoline’s α2-antagonist property additionally provides an internal contrast: if pure α2 blockade were anti-myopic, cirazoline should be strongly protective; instead it was the weakest agent at medium/high doses, arguing against “α2 antagonism alone = myopia control.”

**4. What remains open.**  
We agree that a full agonist–antagonist matrix (lofexidine ± yohimbine; metaraminol ± prazosin; etc.) is needed. We will add this as a limitation and as planned follow-up.

*(Note: the reviewer wrote “tyrosine kinase”; the cited pathway is tyrosine hydroxylase [TH], the rate-limiting enzyme for dopamine synthesis.)*

---

## Comment 4

> It is also discussed that atropine, when present in high concentrations, can bind to α2-adrenergic receptors and block them. This in the end also reduces the amount of myopia development. Please discuss this discrepancy in more detail.

### Answer

We agree that the atropine–α2 literature creates an apparent paradox and that our Discussion must address it more carefully.

**The discrepancy**  
- High-concentration atropine (and MT3) can **antagonize** α2A signaling in vitro; relative potencies of muscarinic antagonists at α2A correlate better with chick FDM inhibition than potencies at M4 (Carr et al., *IOVS*, 2018).  
- Yet **α2 agonists** (brimonidine/clonidine/guanfacine; and here lofexidine) also inhibit experimentally induced myopia (Carr et al., 2019; present LIM study).  
- Pure α2 antagonism (yohimbine) **fails** to inhibit FDM (Carr et al., 2019).

**How we interpret this (to be expanded in Discussion)**  

1. **α2 blockade is neither necessary nor sufficient to explain atropine’s anti-myopia effect.** Correlation of muscarinic antagonists’ α2A affinity with FDM efficacy does not prove that α2 antagonism is the operative mechanism. Atropine also engages nitric oxide–dependent pathways in chicks (Carr & Stell, *Sci Rep*, 2016), and may act on other GPCRs/ion channels at millimolar local concentrations.

2. **Agonist and antagonist pharmacology can affect different nodes of the same circuit.** α2 receptors are pre- and postsynaptic (and on Müller glia in chick retina). Agonist-driven Gi signaling in glia/choroid (perfusion, growth-factor release, NO) may stop eye growth, while antagonist-driven disinhibition of TH in amacrine cells may change dopamine without producing the same net growth phenotype under LIM/FDM.

3. **Concentration regimes differ.** Atropine’s α2A blockade requires ≥~0.1 mM in vitro — overlapping myopia-inhibiting doses but far above muscarinic Kd. Our lofexidine doses are aimed at α2 agonism (nM–low-µM EC50/Ki), not atropine-like multireceptor occupancy.

4. **Our cirazoline result sharpens the paradox.** Cirazoline combines α1 agonism with α2 antagonism and was **least** effective at medium/high doses — again inconsistent with “α2 block = less myopia,” and more consistent with the idea that **α2 activation**, not blockade, is the growth-inhibitory direction in chick models.

5. **Working synthesis for revision:** Atropine’s clinical/experimental anti-myopia effect is multi-target. Off-target α2A binding remains a plausible contributing action for some muscarinic antagonists, but chick pharmacology of selective α2 ligands indicates that **agonism at α2 (and possibly α1-related pathways) inhibits LIM/FDM**, whereas **simple α2 antagonism does not**. The atropine–α2-blockade hypothesis and the α2-agonist myopia-inhibition findings are therefore not mutually exclusive clinical observations, but they **do not support a single linear “block α2 → stop myopia” model**.

---

## Comment 5

> Line 75ff: please add information on the distribution of α2-AR and α1-adrenergic receptors in the fundal layers of chicks and give the correct references (I cannot find any information in the literature that you cited (21, Carr et al.) about the distribution of the adrenergic receptors in chicks). Is there any evidence at all that the avascular retina of the chick expresses alpha1 AR receptors?

### Answer

We agree — Carr et al. (2019) reports functional FDM pharmacology, **not** histological mapping of α1/α2 in chick fundus. Citing it for “distribution in chicks” was incorrect and will be replaced.

**α2-AR distribution in chick ocular tissues (appropriate citations)**  
- **Retina (chick):** α2A is the predominant subtype; immunolocalized to Müller glia (somata in INL; processes to OLM), with additional α2A IR in GCL, OPL, and photoreceptor regions; α2B IR reported in photoreceptor outer segments (Harun-Or-Rashid et al., *IOVS*, 2014; related chick Müller-cell α2A work). Western blot in chick retina detected α2A (Gerhardt et al. / spreading-depression–Müller cell studies).  
- **Choroid (chick):** α2A immunoreactivity on choroidal vessel walls and stroma, near TH-positive varicous fibers (Mathis, Feldkaemper et al., *Graefes Arch Clin Exp Ophthalmol*, 2022).  
- Functional consequence: chick retina is avascular; any α2-mediated vascular effects in chicks are expected mainly in **choroid/anterior uvea**, not retinal capillaries.

**α1-AR in chick avascular retina — honest assessment**  
Direct, definitive evidence that **neural chick retina expresses α1-ARs** is **sparse to absent** in the literature we can verify. Most α1 localization data are mammalian:  
- Rat retina: [³H]prazosin binding enriched in outer plexiform layer (Zarbin et al.).  
- Rabbit/bovine RPE: α1-linked ion transport.  
- Mammalian retinal vessels / arterioles: α1 subtype mRNA and functional vasoconstriction (reviewed in Casini, Dal Monte, et al., *Cells*, 2020 — “The Role of Adrenoceptors in the Retina”).  
- Rabbit eye: α1a dominates (>90% of ocular α1 message), mainly iris, ciliary body, choroid (Suzuki et al., *Br J Pharmacol*, 2002).

Because the chick retina lacks intrinsic vessels, mammalian “retinal vascular α1” findings do **not** transfer. Plausible chick sites for α1-mediated myopia-relevant effects are therefore **choroid, RPE, ciliary body/iris**, and possibly sclera — not an established α1 network inside avascular neural retina. We will revise the Introduction accordingly, remove the incorrect Carr distribution claim, cite the chick α2 papers above, and explicitly state the **evidence gap for chick retinal α1**.

---

## Comment 6

> Line 92: Please give a reference that lofexidine is capable of regulating retinal dopamine activity and choroidal blood flow. I cannot find this information in ref. [30]. In addition, please add information on the species in which the effects of the three drugs were tested.

### Answer

The reviewer is correct. Reference [30] (Giovannitti et al., *Anesth Prog*, 2015) is a general clinical review of α2 agonists and **does not** demonstrate that lofexidine regulates retinal dopamine or choroidal blood flow. That sentence will be corrected.

**Accurate statement for revision:**  
Retinal dopaminergic modulation and/or choroidal perfusion effects have been reported for **other** α2 agonists — especially **brimonidine** and **clonidine** — in **chick** (Carr et al., 2019; related chick dopamine/choroid studies) and **guinea pig** (Peng/Xiang et al., brimonidine myopia / MMP-2 / choroidal thickness work). Lofexidine was selected here as a highly α2A/α2C-preferring, clinically approved α2 agonist; **direct evidence that lofexidine itself alters retinal dopamine or choroidal blood flow is lacking**, and our study measured refractive/biometric outcomes, not dopamine or perfusion.

**Species context for the three agents (to add):**  
| Drug | Primary pharmacology literature | Myopia / ocular growth models |  
|---|---|---|  
| **Lofexidine** | Human clinical use (opioid withdrawal); rodent/dog cardiovascular & withdrawal models; recombinant human α2 assays | **Present study: chick LIM** (first systematic LIM test for this agent, to our knowledge) |  
| **Metaraminol** | Human vasopressor; mammalian cardiovascular assays; human recombinant α1/α2 binding | **Present study: chick LIM**; related α1 pathway myopia work mostly in **mouse** (e.g., bunazosin antagonist, Jeong et al., 2023) |  
| **Cirazoline** | Guinea-pig aorta/ileum; cat/monkey central pharmacology; recombinant human α1 | **Present study: chick LIM** |  
| Comparator α2 agonists (brimonidine, clonidine, guanfacine) | Various mammalian systems | **Chick FDM** (Carr et al., 2019); **guinea pig** FDM/LIM-related brimonidine studies |

---

## Comment 7

> Line 113–114: Why did you choose 3 nmol, 30 nmol, and 300 nmol as a dose? As noted at the beginning of this review, the manuscript lacks information on the KD and/or EC50 values for the agonists.

### Answer

Dose selection was driven by **prior chick intravitreal α2-agonist myopia work**, not by in-eye KD matching (which was a limitation).

Carr et al. (2019) used **2, 20, and 200 nmol** (in 20 µL) of brimonidine/clonidine/guanfacine/yohimbine against chick FDM. We adopted a similar log-spaced triad — **3, 30, 300 nmol in 10 µL** — to:  
1. Span the same order of magnitude shown to inhibit chick experimental myopia;  
2. Probe a low dose near the threshold for highly potent α2 agonists;  
3. Include a high dose where less potent / less selective agents (metaraminol, cirazoline) might still engage receptors.

**Nominal vitreous concentrations** (10 µL into ~150 µL liquid vitreous):  
- 3 nmol → ~20 µM  
- 30 nmol → ~200 µM  
- 300 nmol → ~2 mM  

Relative to published in vitro constants:  
- Lofexidine EC50/Ki in the **nanomolar** range → even 3 nmol is nominally well above Kd if freely mixed (consistent with efficacy at all three doses).  
- Metaraminol α1A KD ~60 nM, α2A KD ~µM → low dose may be closer to a practical threshold after clearance/binding; medium/high doses more clearly suprathreshold (matches our dose-threshold phenotype).  
- Cirazoline α1 EC50 ~70–240 nM; α2 antagonist KB ~28 nM → all doses can engage both actions.

We will add this dose rationale, affinity table, and concentration estimates to Methods/Discussion, and note that **tissue free concentration, chick receptor Kd, and half-life were not measured**.

---

## Comment 8 (Discussion)

> As said before, the manuscript lacks information on the KD and/or EC50 values for the agonists which hampers the discussion on distinct subtype-specific dose-response relationships.

### Answer

We agree. Without affinity/potency context, “subtype-specific dose-response” claims are under-supported. We will revise the Discussion to ground the phenotypes in pharmacology:

1. **Lofexidine’s flat, high efficacy from 3 nmol** fits a high-affinity α2 agonist (nM Ki/EC50) operating well above occupancy threshold, with possible contributions from imidazoline/D2/5-HT off-targets at higher doses.  
2. **Metaraminol’s threshold between 3 and 30 nmol** fits lower α1 potency plus possible late α2 engagement (~50× weaker α2A affinity) and indirect NE release.  
3. **Cirazoline’s weaker medium/high-dose effect** fits simultaneous α1 agonism and α2 antagonism (Ruffolo & Waddell, 1982), i.e., opposing actions on pathways that both relate to choroidal/retinal growth control — not true “dual agonism.”  
4. We will temper language that over-attributes outcomes to a single subtype and list off-target profiles and the missing PK/Kd-in-chick measurements as limitations.

---

## Summary of planned manuscript revisions

1. Add a pharmacology table (KD/Ki/EC50 + off-targets) for metaraminol, lofexidine, and cirazoline with primary citations.  
2. Correct cirazoline classification (α1 agonist / α2 antagonist).  
3. Replace incorrect Carr et al. “distribution in chicks” citation with chick α2 localization papers; acknowledge lack of clear chick retinal α1 evidence.  
4. Correct the unsupported claim that lofexidine regulates retinal dopamine/choroidal flow; attribute those data to brimonidine/clonidine and list species.  
5. Expand Discussion on agonist vs antagonist rationale, atropine–α2 paradox, metaraminol’s possible α2 contribution, and dose selection vs Kd/EC50.  
6. Soften subtype-causal language pending antagonist co-administration studies.

---

## Key references for the responses above

- Proudman et al. *Pharmacol Res Perspect.* 2021 — human α1 agonist selectivity (metaraminol log KD).  
- Proudman et al. *Pharmacol Res Perspect.* 2022 — human α2A/B/C agonist signaling/affinity (metaraminol α2A log KD ≈ −5.50).  
- Ruffolo & Waddell. *J Pharmacol Exp Ther.* 1982 — cirazoline α1 agonist / α2 antagonist (pA2 7.56).  
- Lofexidine prescribing information / Gish et al. 2019 — α2A/α2C Ki–EC50; off-target D2S/5-HT.  
- Carr et al. *IOVS.* 2018 — muscarinic antagonists block α2A at myopia-relevant concentrations.  
- Carr, Nguyen & Stell. *Clin Exp Optom.* 2019 — α2 agonists inhibit chick FDM; yohimbine does not; doses 2–200 nmol.  
- Iuvone & Rauch. *Life Sci.* 1983 — α2 regulation of retinal TH (rat).  
- Harun-Or-Rashid et al. *IOVS.* 2014 — chick retinal α2A (Müller cells) / α2B (photoreceptors).  
- Mathis / Feldkaemper et al. *Graefes Arch Clin Exp Ophthalmol.* 2022 — chick choroidal α2A.  
- Suzuki et al. *Br J Pharmacol.* 2002 — rabbit ocular α1 subtype distribution.  
- Casini et al. *Cells.* 2020 — review of retinal adrenoceptors (mostly mammalian).  
- Jeong et al. *IOVS.* 2023 — α1 antagonist bunazosin and mouse myopia.  
- Giovannitti et al. *Anesth Prog.* 2015 — general α2 agonist review (insufficient for retinal DA/choroid claims about lofexidine).
