import subprocess, os, tempfile, json

TAG = "guerillahold2-20"

posts = [
    {
        "title": "7 Essential Tools for Non-Emergency Medical Transport Drivers (2026)",
        "slug": "nemt-driver-tools-2026",
    },
    {
        "title": "Gun Safety at Home: 5 Storage Solutions That Work (2026)",
        "slug": "gun-safety-home-storage-2026",
    },
    {
        "title": "AI Tools That Actually Make Money for Small Businesses (2026)",
        "slug": "ai-tools-small-business-revenue-2026",
    }
]

contents = [
    f"""<p>Running a non-emergency medical transport operation in California requires more than a clean record. The highest earners share one thing: better equipment.</p>
<h2>1. Vehicle Tablet Mount</h2><p>RAM mounts are the industry standard for commercial transport. Keep dispatch and navigation accessible without blocking sight lines.</p>
<p><a href="https://www.amazon.com/s?k=RAM+Mounts+commercial+vehicle+tablet+mount&tag={TAG}">Browse vehicle tablet mounts on Amazon</a></p>
<h2>2. HIPAA Documentation Kit</h2><p>Institutional clients expect organized chain-of-custody paperwork. A medical transport documentation kit keeps you audit-ready.</p>
<p><a href="https://www.amazon.com/s?k=medical+transport+documentation+organizer&tag={TAG}">Medical documentation supplies on Amazon</a></p>
<h2>3. Portable Power Station</h2><p>8-12 hour shifts demand reliable power for tablets and equipment without drawing from vehicle batteries.</p>
<p><a href="https://www.amazon.com/s?k=portable+power+station+300W+Jackery&tag={TAG}">Portable power stations on Amazon</a></p>
<h2>4. Commercial First Aid Kit</h2><p>California specialty operators must maintain OSHA-compliant first aid supplies. Signals professionalism to institutional clients.</p>
<p><a href="https://www.amazon.com/s?k=OSHA+commercial+vehicle+first+aid+kit&tag={TAG}">Commercial first aid kits on Amazon</a></p>
<h2>5. Dual-Channel GPS Dash Camera</h2><p>GPS logging creates irrefutable documentation of every run for institutional contracts and insurance disputes.</p>
<p><a href="https://www.amazon.com/s?k=dual+dash+cam+GPS+commercial&tag={TAG}">GPS dash cameras for commercial vehicles on Amazon</a></p>
<h2>6. 12V Portable Refrigerator</h2><p>Tier 3 and above operators handling pharmaceutical samples need precision climate control for premium specialty contracts.</p>
<p><a href="https://www.amazon.com/s?k=12V+portable+refrigerator+pharmaceutical&tag={TAG}">12V portable refrigerators for transport on Amazon</a></p>
<h2>7. Professional Transport Uniform</h2><p>Institutional clients evaluate professionalism before booking. The right uniform signals competence to hospital coordinators.</p>
<p><a href="https://www.amazon.com/s?k=medical+transport+professional+uniform&tag={TAG}">Professional transport uniforms on Amazon</a></p>
<hr><p>CALLUX connects certified specialty transport operators with institutional contracts across Sacramento and NorCal with 65/35 revenue splits. <a href="https://trustchainservices.com">Learn more at TrustChain Services</a>.</p>
<p><em>As an Amazon Associate, Guerilla Holdings LLC earns from qualifying purchases.</em></p>""",

    f"""<p>Gun safety education starts with proper storage. Whether you are a first-time owner, a parent, or a community educator, these five solutions cover the full spectrum.</p>
<h2>1. Biometric Pistol Safe</h2><p>Rapid access in emergencies while keeping firearms secured from children. Backup key entry recommended for reliability.</p>
<p><a href="https://www.amazon.com/s?k=biometric+pistol+safe+quick+access&tag={TAG}">Top-rated biometric pistol safes on Amazon</a></p>
<h2>2. Long Gun Steel Cabinet</h2><p>Rifles and shotguns need dedicated secure storage. Steel cabinets with quality locks are the minimum standard for households with children.</p>
<p><a href="https://www.amazon.com/s?k=long+gun+steel+cabinet+lock&tag={TAG}">Steel gun cabinets on Amazon</a></p>
<h2>3. Gun Cable Lock Multi-Pack</h2><p>Most accessible first defense. Inexpensive, easy to use. A multi-pack secures every firearm in the household simultaneously.</p>
<p><a href="https://www.amazon.com/s?k=gun+cable+lock+multi+pack&tag={TAG}">Gun cable lock kits on Amazon</a></p>
<h2>4. Lockable Ammunition Storage</h2><p>Storing ammunition separately from firearms is foundational safety. Purpose-built containers are moisture-resistant and lockable.</p>
<p><a href="https://www.amazon.com/s?k=ammunition+storage+container+lockable&tag={TAG}">Ammunition storage containers on Amazon</a></p>
<h2>5. Family Gun Safety Education Kit</h2><p>Age-appropriate curricula teach children: Stop. Do Not Touch. Run Away. Tell a Grown-Up. Essential for households with firearms.</p>
<p><a href="https://www.amazon.com/s?k=gun+safety+education+children+family&tag={TAG}">Gun safety education materials on Amazon</a></p>
<hr><p>GAFC is a minority-owned social enterprise bringing free gun safety education to underserved communities in Sacramento. Follow us <a href="https://instagram.com/glocksandfriedchicken">@glocksandfriedchicken</a>.</p>
<p><em>As an Amazon Associate, Guerilla Holdings LLC earns from qualifying purchases.</em></p>""",

    f"""<p>After deploying autonomous AI systems across specialty transport, social enterprise, and digital commerce, here is what actually moves revenue for small businesses in 2026.</p>
<h2>1. AI Business Strategy Books</h2><p>Content generation has the highest ROI for small businesses. These books give the foundation to build systems that generate organic traffic at a fraction of traditional cost.</p>
<p><a href="https://www.amazon.com/s?k=AI+automation+small+business+marketing+book&tag={TAG}">AI business strategy books on Amazon</a></p>
<h2>2. Thermal Label Printer</h2><p>Any product-based business running dropshipping or print-on-demand needs a thermal label printer. Rollo and MUNBYN models eliminate ink costs and speed fulfillment.</p>
<p><a href="https://www.amazon.com/s?k=thermal+label+printer+4x6+Rollo+MUNBYN&tag={TAG}">Thermal label printers on Amazon</a></p>
<h2>3. Ring Light and Webcam Setup</h2><p>Social media content drives sales across every business category. A quality lighting setup produces scroll-stopping content at minimal cost.</p>
<p><a href="https://www.amazon.com/s?k=ring+light+webcam+content+creation+kit&tag={TAG}">Content creation lighting kits on Amazon</a></p>
<h2>4. Electric Standing Desk</h2><p>Operators running AI-powered businesses work long hours. Sit-stand desks reduce fatigue and sustain output quality. Infrastructure, not a luxury.</p>
<p><a href="https://www.amazon.com/s?k=electric+standing+desk+home+office+adjustable&tag={TAG}">Electric standing desks on Amazon</a></p>
<h2>5. Portable SSD for Business Backup</h2><p>Business data is a liability without proper backup. A portable SSD provides fast local backup independent of cloud storage that can be compromised.</p>
<p><a href="https://www.amazon.com/s?k=portable+SSD+2TB+Samsung+T7&tag={TAG}">Portable SSDs for business backup on Amazon</a></p>
<hr><p>Guerilla Holdings LLC operates AI-native businesses across specialty transport and social enterprise. <a href="https://trustchainservices.com">Learn more at TrustChain Services</a>.</p>
<p><em>As an Amazon Associate, Guerilla Holdings LLC earns from qualifying purchases.</em></p>"""
]

for post, content in zip(posts, contents):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, dir="/tmp") as f:
        f.write(content)
        tmpfile = f.name

    title = post["title"]
    slug = post["slug"]
    
    result = subprocess.run(
        ["docker", "exec", "-i", "penelope-wordpress", "bash", "-c",
         f"cat > /tmp/post_content.html && php wp-cli.phar post create --post_title='{title}' --post_status=publish --post_name='{slug}' --post_content-file=/tmp/post_content.html --allow-root"],
        input=content,
        capture_output=True, text=True
    )
    os.unlink(tmpfile)
    out = (result.stdout + result.stderr).strip()
    print(f"POST [{slug}]: {out}")
