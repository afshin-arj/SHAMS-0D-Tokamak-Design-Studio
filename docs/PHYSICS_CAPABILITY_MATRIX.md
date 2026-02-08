# Physics Capability Matrix

This is a **read‑only**, reviewer‑oriented map of SHAMS capabilities in the **frozen Point Designer evaluator**.

**Key idea:** SHAMS is *feasibility‑authoritative* (constraint‑first) rather than *optimization‑first*.

## Legend

- **Authority**
  - **A:** Authoritative within SHAMS’ declared 0‑D scope (deterministic, explicitly stated closure).
  - **P:** Proxy (trend‑correct screening closure).
- **Intent domain**
  - **R:** Research intent (diagnostic‑heavy, plant gates relaxed by policy).
  - **F:** Reactor intent (plant feasibility gates enforced).

## Subsystem matrix

| Subsystem | Equations / closures used (representative) | Authority | Intended validity domain |
|---|---|:---:|---|
| Geometry & volumes | $R_0,a,\kappa,\delta \rightarrow V,A,S$ via analytic tokamak geometry; aspect ratio $A=R_0/a$ | A | R,F (axisymmetric, single‑null‑agnostic screening) |
| Global confinement | $\tau_E = H\,\tau_{98y2}(I_p,B_t,n,P,R_0,a,\kappa,\ldots)$ with explicit $H$ | A | R,F (H‑mode screening; not a transport solver) |
| Stored energy closure | $W=\tfrac{3}{2}\int (n_eT_e+n_iT_i)\,dV$; $P_{loss}\approx W/\tau_E$ (plus optional radiation) | A | R,F |
| Fusion power | $P_{fus}\propto\int n_D n_T\langle\sigma v\rangle(T_i)\,dV$ with analytic profiles when enabled | A | R,F (D‑T equivalent screening) |
| Power balance | $P_{heat}=P_\alpha+P_{aux}$; closure to meet targets (e.g., $H_{98}$, $Q_{DT,eqv}$) under bounds | A | R,F (steady‑state 0‑D closure) |
| Analytic profiles (½‑D scaffold) | Deterministic analytic $n(\rho),T(\rho)$ families; integrated moments and peaking factors | A | R,F (shape parameters are proxies unless constrained) |
| Bootstrap current | Proxy: bounded $f_{BS}$; Sauter‑inspired option uses profile gradients when profiles ON | P (proxy for $q(\rho)$ and collisionality) | R,F (trend‑correct; not full neoclassical) |
| Current drive accounting | $P_{CD}$ and wallplug efficiency proxies; bookkeeping into recirc power | P | F primarily (screening) |
| MHD stability screening | $q_{95}$ constraint; $\beta_N$ and policy gates; other stability dials where present | P | R,F (screening; no ideal/resistive MHD solver) |
| Control contracts (VS) | Deterministic mapping $vs\_margin\rightarrow \tau_{VS}$; $\gamma_{VS}=1/\tau_{VS}$; $f_{bw,req}\approx f_{bw}\,\gamma_{VS}/(2\pi)$; $P_{VS,req}\approx f_{m}\,W_{PF}/\tau_{VS}$ | P | R,F (envelope requirements; no waveform optimization) |
| RWM screening (MHD/control) | No-wall vs ideal-wall $\beta_N$ envelope; $\chi=(\beta_N-\beta_{N,NW})/(\beta_{N,IW}-\beta_{N,NW})$; $\gamma_{rwm}\sim \Phi(\chi)\Psi(rot)/\tau_w$; $f_{bw,req}=\gamma_{rwm}/(2\pi)$; $P_{req}\sim C_P W_{PF}\gamma_{rwm}$ | P | R (diagnostic), F (optional feasibility gate via caps) |
| PF waveform envelope (canonical) | Ramp–flat–ramp proxy; $V\approx L_{eff}\,dI/dt+R_{eff}I$; $P=VI$; $E\approx 2\left(\tfrac12 L_{eff}I^2+\tfrac12R_{eff}I^2t_{ramp}\right)+R_{eff}I^2t_{flat}$ | P | R,F (actuator envelope screening; no PF coil design) |
| SOL radiative control contract | If enabled: required $f_{rad,SOL}$ to hit $q_{div,target}$ (linearized $q_{div}\propto (1-f_{rad,SOL})$); optional cap $f_{rad,SOL}\le f_{rad,SOL,max}$ | P | R (diagnostic), F (optional feasibility gate) |
| Greenwald density | $f_G = \bar n_e / n_G$ with $n_G\propto I_p/(\pi a^2)$ | A | R,F |
| Divertor / exhaust | Proxy heat‑flux $q_{div}$ from $P_{SOL}$ and geometry; optional $P_{SOL}/R$ style gates | P | R,F (screening) |
| Radiation (optional) | $P_{rad}=\int n_e n_Z L_Z(T_e)\,dV$; DB selection with SHA256 provenance; OFF by default | A for provenance; P for data unless user supplies validated DB | R (available), F (only when enabled by policy) |
| Neutronics blanket proxy | TBR proxy from blanket/shield thickness & coverage; policy‑gated | P | F (screening; no 3‑D neutronics) |
| Magnet technology axis | Tech enum: HTS/LTS/COPPER; outputs stamp $magnet_technology$, $tf_sc_flag$ | A | R,F |
| Superconductor margin | Tech‑aware margin proxy (HTS/LTS) driven by $B_{peak},T_{coil}$; policy gates | P | R,F (screening) |
| Copper TF ohmic loss | $P_{\Omega}=I^2R(T)$ proxy; coupled into plant recirc | P | R (common), F (normally blocked by policy) |
| Structural stress | Hoop / Von Mises proxy vs limit; policy gates | P | R,F (screening) |
| Plant closure | Gross → recirc → net; recirc includes CD and (if copper) TF ohmic; explicit efficiencies | A | F (net‑electric framing), R (diagnostic) |

## Proxy vs authoritative: what SHAMS means

- **A** means “authoritative within SHAMS’ declared 0‑D screening scope,” not “first‑principles transport or full 3‑D engineering.”
- **P** means “explicit screening closure with bounded behavior,” and it is always stamped into artifacts and model cards.

## Lessons adopted from Bluemira (without changing SHAMS’ philosophy)

Bluemira is a broad integrated fusion plant framework. SHAMS remains feasibility‑authoritative, but we adopt these lessons in a SHAMS‑compatible way:

1. **Capability matrix clarity:** a single page that states what the tool can and cannot do (this page).
2. **Layered subsystem accounting:** explicit separation of Plasma / Current / Exhaust / Magnets / Neutronics / Plant, with provenance.
3. **Data provenance as first‑class:** radiation databases are selected by ID/path and stamped with SHA256 in artifacts.
4. **Geometry–physics decoupling:** geometry closure and physics closure remain separate and are reported separately in ledgers.



### Control Contracts (v226–v227)
- **Envelope-based control contracts (VS, PF waveform, SOL radiation control)**: deterministic post-processing; does not mutate physics.
- **Authority tags (v227)**: `control_contracts_authority` (`proxy`, `proxy_input`, `proxy_inferred`, `diagnostic_proxy`, `disabled`).
- **Budget ledger (v227)**: `control_budget_ledger` reports `t_cycle_s`, peak and average control powers, and pulse energies.
- **Scan Lab overlay (v227)**: Cartography2 mechanism groups include `CONTROL` (VS bandwidth/power, PF waveform, SOL radiation cap).

### RWM Screening (v229.0)

- **Purpose:** PROCESS-class *screening* for resistive-wall-mode control authority; deterministic, no time evolution.
- **Outputs:** `rwm_regime` \in {`NO_WALL_STABLE`, `RWM_ACTIVE`, `IDEAL_WALL_EXCEEDED`, `UNAVAILABLE`}, plus $\beta_{N,NW}$, $\beta_{N,IW}$, $\chi$, $\tau_w$, $\gamma_{rwm}$, required bandwidth and control power.
- **Gates (optional):** caps `rwm_bandwidth_max_Hz` and `rwm_control_power_max_MW` (default to VS caps if absent). Exceeding $\beta_{N,IW}$ is always flagged as non-operable when enabled.
- **Authority:** `control.rwm` is **proxy** by construction; all coefficients are explicit and bounded.


