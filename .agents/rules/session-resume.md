# Operational Rule: Session Resume & Task Discovery

## Core Mandate
Every newly initiated agent session or turn execution MUST begin by inspecting the `tasks/` directory to discover active task directories (`tasks/TSK-XXX`). Prior conversational memory must NEVER be assumed or relied upon.

## Protocol
1. **Directory Discovery:**
   - Scan `tasks/` for directories matching `TSK-[0-9]{3,}`.
   - Ignore `tasks/_template`.
2. **State Identification:**
   - For each candidate task directory, inspect the stage contract files in sequential order:
     1. `01_intake.md`
     2. `02_plan.md`
     3. `03_exec.md`
     4. `04_verify.md`
     5. `05_retro.md`
   - Identify the latest incomplete stage contract. The stage contract whose prerequisites are satisfied and whose exit criteria are not yet marked complete is the **Active Stage Contract**.
3. **Execution Resume:**
   - Read ONLY the Active Stage Contract and its immediate dependency inputs.
   - Continue execution strictly within the scope boundaries and token budget allocated for that stage.
4. **Zero-Assumption Invariant:**
   - If an agent is invoked with an ambiguous prompt or no prior memory, do not re-ask basic intake questions if an active `TSK-XXX` already exists on disk.
   - Ground all agent actions exclusively in the on-disk state.
