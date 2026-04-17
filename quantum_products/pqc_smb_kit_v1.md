## DISCLAIMER

This guide is educational content based on publicly available NIST standards. It is not legal, security, or professional advice. Consult a qualified cybersecurity professional for your specific situation.

---

# Post-Quantum Cryptography Readiness Kit for Small Businesses

Hello, business owner! You’re busy running your company, and cybersecurity might feel like a complex topic. You might have heard whispers about "quantum computers" and "new encryption," and it's understandable if it sounds a bit overwhelming. The good news is that understanding the basics and taking a few proactive steps can help protect your business for the future.

This guide will introduce you to Post-Quantum Cryptography (PQC) in simple terms. We'll focus on practical steps you can take today, based on recommendations from the National Institute of Standards and Technology (NIST), a leading authority in cybersecurity.

---

## What Is Post-Quantum Cryptography?

Post-Quantum Cryptography, or PQC, refers to new types of encryption that can withstand attacks from powerful future computers known as quantum computers. Currently, your business uses standard encryption to protect sensitive information, but these future quantum machines could potentially break that encryption. PQC is the solution being developed to keep your data safe in the quantum era.

---

## Why Small Businesses Need to Know Now

You might be thinking, "Quantum computers aren't here yet, why worry?" The truth is, the time to prepare is now, for a few important reasons:

1.  **The "Harvest Now, Decrypt Later" Threat:** Even though powerful quantum computers capable of breaking today's encryption don't widely exist yet, bad actors are already collecting large amounts of encrypted data. They plan to store this data and decrypt it later, once quantum computers become available. If your business handles sensitive information that needs to remain secret for many years – like customer records, financial data, or intellectual property – this "harvest now, decrypt later" threat is very real.

2.  **Major Tech Shifts Are Coming:** Big technology companies are already planning for the quantum future. For example, Google has announced plans to begin integrating PQC into its Chrome browser by April 2026. This means that the software and services you use every day will start adopting these new standards. Staying informed will help you understand these changes as they happen.

3.  **NIST's Timeline for Adoption:** NIST has been actively working on selecting and standardizing new PQC algorithms. NIST's goal is for widespread adoption of these new cryptographic standards by 2035. While 2035 seems far off, transitioning to new encryption takes time and planning. Starting early will make the process smoother and less disruptive for your business.

In essence, preparing for PQC is about protecting your business from future threats and ensuring your long-term digital security. It's not about immediate panic, but rather thoughtful preparation.

---

## The 5-Step NIST Readiness Checklist

NIST has provided a roadmap for organizations to prepare for the quantum computing era. Here’s a checklist adapted for small businesses, helping you understand where to start.

### Step 1: Inventory Your Encrypted Systems

Before you can plan for the future, you need to know what you have now. This step is about identifying all the places where your business uses encryption. Think of it like taking stock of your digital locks.

**What to do:**

*   **List Your Digital Assets:** Make a list of all systems, applications, and services that store or transmit sensitive information. This might include:
    *   Your website (especially if it handles customer logins or payments)
    *   Email systems (for internal communication and client interactions)
    *   Virtual Private Networks (VPNs) you use for secure remote access
    *   Cloud storage services (like Google Drive, Microsoft OneDrive, Dropbox)
    *   Accounting software or customer relationship management (CRM) systems
    *   Any hardware that uses encryption, such as secure USB drives or hard drives
    *   Software you use for communication, like video conferencing tools
*   **Understand Encryption Use:** For each item on your list, think about *how* it uses encryption. Does it encrypt data at rest (when it's stored) or data in transit (when it's being sent)? *According to NIST*, understanding your current cryptographic footprint is the first critical step toward PQC readiness.
*   **Simple Record Keeping:** You don't need a fancy system. A simple spreadsheet or even a notebook can work to keep track of these systems. The goal is to get a clear picture.

**Why this matters for PQC:** Knowing where your current encryption lives will help you identify which systems will need to be updated with PQC in the future.

### Step 2: Identify Your "Long-Secret" Data

Not all data needs the same level of protection, and some data needs to remain secret for much longer than others. This step focuses on identifying the information that, if exposed years from now, could harm your business.

**What to do:**

*   **Define "Long-Secret":** Think about data that, if captured today and decrypted in five, ten, or even twenty years, would still be valuable to an attacker or damaging to your business. This is the data most vulnerable to the "harvest now, decrypt later" threat.
*   **Examples of Long-Secret Data:**
    *   Customer personal data (names, addresses, sensitive identifiers)
    *   Employee records and payroll information
    *   Proprietary business secrets, formulas, or intellectual property
    *   Long-term contracts or agreements
    *   Sensitive financial records that must be retained for legal reasons
*   **Prioritize This Data:** *NIST recommends* that organizations prioritize the protection of their "long-secret" data. This data will likely be among the first to require PQC upgrades.
*   **Where is it Stored?** Cross-reference this data with your inventory from Step 1. Which of your encrypted systems hold this highly sensitive, long-lasting information?

**Why this matters for PQC:** This step helps you focus your PQC efforts on the data that truly needs the strongest, most future-proof protection.

### Step 3: Check Your Software Vendors' PQC Roadmaps

Most small businesses rely on third-party software and cloud services. Your PQC readiness will largely depend on your vendors' readiness.

**What to do:**

*   **Identify Key Vendors:** For the systems you identified in Step 1, list your main software providers. This includes your web hosting company, email provider, cloud storage provider, and any critical business application vendors.
*   **Ask About PQC Plans:** Reach out to your key vendors. You can start by checking their websites for announcements or contacting their support teams.
    *   Ask if they have a "Post-Quantum Cryptography roadmap" or a plan for transitioning to new cryptographic standards.
    *   Specifically inquire if they are planning to support the new algorithms selected by NIST. These include **ML-KEM (standardized in FIPS 203) for establishing secret keys**, and **ML-DSA (standardized in FIPS 204) and SLH-DSA (standardized in FIPS 205) for creating digital signatures**.
*   **Document Responses:** Keep a record of your vendors' responses. This will help you understand their timelines and how they align with your own business needs. *According to NIST*, engaging with your supply chain is crucial for a successful PQC transition.

**Why this matters for PQC:** You can only implement PQC if your software and service providers support it. Understanding their plans helps you prepare for updates and potential changes.

### Step 4: Ask Your IT Provider About FIPS 203/204/205 Support

If your business works with an IT consultant, managed service provider (MSP), or has an internal IT team, they are your primary resource for technical implementation.

**What to do:**

*   **Initiate the Conversation:** Schedule a meeting or call with your IT provider.
*   **Educate and Ask:**
    *   Explain that you are learning about Post-Quantum Cryptography and the upcoming changes.
    *   Ask if they are familiar with the new NIST PQC standards: **FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA).**
    *   Inquire about their plan for helping your business transition to these new standards when they become available in commercial products.
    *   Ask what steps they recommend you take now to prepare.
*   **Understand Their Knowledge:** Your IT provider should ideally be aware of these developments. If they're not, it might be a good opportunity for both of you to learn together or consider seeking additional specialized advice. *NIST recommends* that IT professionals stay informed about these evolving cryptographic standards.

**Why this matters for PQC:** Your IT provider will be key to implementing any PQC solutions. Ensuring they are knowledgeable and prepared is essential.

### Step 5: Document Your Quantum Risk Register

This step is about bringing together all the information you've gathered and thinking about the potential risks. A "risk register" sounds formal, but it can be a simple document.

**What to do:**

*   **List Potential Threats:** Based on your long-secret data (Step 2), what are the potential consequences if this data were exposed by a quantum computer breaking your current encryption? (e.g., reputation damage, financial loss, legal penalties).
*   **Identify Vulnerabilities:** Which of your systems (from Step 1) are most critical and might be slow to update to PQC?
*   **Outline Mitigation Steps:** For each risk, what actions can you take?
    *   For example, if a specific vendor is slow to adopt PQC, do you need a backup plan or an alternative?
    *   How will you monitor your vendors' progress?
    *   What budget or resources might be needed for future upgrades?
*   **Regular Review:** This isn't a one-time task. Plan to review your quantum risk register periodically, perhaps once a year, to update it as technology and vendor roadmaps evolve. *According to NIST*, creating and regularly reviewing a risk register is a fundamental part of managing cybersecurity risks, including those posed by quantum computing.

**Why this matters for PQC:** Documenting risks helps you prioritize actions, allocate resources, and communicate clearly about your PQC strategy. It turns potential problems into manageable tasks.

---

## What to Do This Week

Getting started doesn't require a large project. Here are three concrete actions you can take this week to begin your PQC readiness journey:

1.  **Start Your Inventory:** Grab a pen and paper or open a simple document. Begin listing the main software, cloud services, and hardware your business uses that handle sensitive information. You don't need to finish it all, just get started on Step 1 of the checklist.
2.  **Identify One Piece of "Long-Secret" Data:** Think about one type of information your business holds that absolutely *must* remain confidential for many years. Knowing this helps you focus your attention on what matters most.
3.  **Reach Out to One Key Vendor:** Pick one crucial software provider (like your cloud storage or email host) and look for information on their website about "Post-Quantum Cryptography" or "PQC roadmap." If you can't find anything, draft a quick email to their support asking about their plans for FIPS 203, 204, and 205 support.

---

## Glossary of 8 Key Terms

Here are some important terms explained in plain language:

*   **Cryptography:** The practice of secure communication in the presence of third parties. It involves creating and breaking codes to protect information.
*   **Encryption:** The process of converting information or data into a code to prevent unauthorized access. Only authorized parties with the correct key can decrypt and read the information.
*   **Quantum Computer:** A new type of computer that uses the principles of quantum mechanics to solve certain problems much faster than traditional computers. Future quantum computers are expected to be able to break many of today's common encryption methods.
*   **Post-Quantum Cryptography (PQC):** New encryption methods designed to be secure against attacks from both classical (traditional) and future quantum computers. NIST has been standardizing these algorithms.
*   **ML-KEM (Module-Lattice-based Key Encapsulation Mechanism):** An algorithm standardized by NIST in **FIPS 203**. According to NIST, ML-KEM is used for "Key Encapsulation Mechanisms," which means it helps two parties securely agree on a shared secret key over an insecure channel, even in the presence of a quantum computer.
*   **ML-DSA (Module-Lattice-based Digital Signature Algorithm):** An algorithm standardized by NIST in **FIPS 204**. According to NIST, ML-DSA is used for "Digital Signature Algorithms," which means it allows you to prove the authenticity and integrity of digital messages and documents, resisting quantum attacks.
*   **SLH-DSA (Stateless Hash-based Digital Signature Algorithm):** Another algorithm standardized by NIST in **FIPS 205**. According to NIST, SLH-DSA is also for "Digital Signature Algorithms" and offers robust security properties, providing an alternative to ML-DSA for specific applications.
*   **FIPS (Federal Information Processing Standard):** A series of standards published by NIST for computer systems used by non-military U.S. government agencies and contractors. These standards are widely adopted by the private sector for cybersecurity best practices.

---

## Resources

For more in-depth information and the latest updates on Post-Quantum Cryptography, NIST provides extensive free resources:

*   **NIST Post-Quantum Cryptography Project Page:** [https://csrc.nist.gov/projects/post-quantum-cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
*   **FIPS 203: Module-Lattice-based Key-Encapsulation Mechanism Standard (ML-KEM):** [https://csrc.nist.gov/pubs/fips/203/final](https://csrc.nist.gov/pubs/fips/203/final)
*   **FIPS 204: Module-Lattice-based Digital Signature Standard (ML-DSA):** [https://csrc.nist.gov/pubs/fips/204/final](https://csrc.nist.gov/pubs/fips/204/final)
*   **FIPS 205: SLH-DSA Digital Signature Standard (SLH-DSA):** [https://csrc.nist.gov/pubs/fips/205/final](https://csrc.nist.gov/pubs/fips/205/final)

---