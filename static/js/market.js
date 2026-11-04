/**
 * Knight Online Canlı Pazar & Arbitraj Takip Sistemi
 * Frontend Scripti
 */

document.addEventListener("DOMContentLoaded", () => {
  // Durum Yönetimi
  const state = {
    activeTab: "market",
    q: "",
    type: "",
    category: "",
    channel: "",
    sort: "price_asc",
    isLoading: false
  };

  // DOM Elemanları
  const searchInput = document.getElementById("search-input");
  const typeBtns = document.querySelectorAll(".market-type-toggle .type-btn");
  const channelSelect = document.getElementById("channel-select");
  const sortSelect = document.getElementById("sort-select");
  const catPills = document.querySelectorAll(".category-pills .cat-pill");
  const refreshBtn = document.getElementById("btn-refresh");
  const tabBtns = document.querySelectorAll(".view-tab-btn");

  const viewMarket = document.getElementById("view-market");
  const viewArbitrage = document.getElementById("view-arbitrage");
  const viewStalls = document.getElementById("view-stalls");
  const marketFilterBar = document.getElementById("market-filter-bar");

  const marketTbody = document.getElementById("market-tbody");
  const arbitrageTbody = document.getElementById("arbitrage-tbody");
  const stallsGrid = document.getElementById("stalls-grid");
  const resultsCount = document.getElementById("results-count");

  // Sayaç Elemanları
  const statTotalItems = document.getElementById("stat-total-items");
  const statMerchants = document.getElementById("stat-merchants");
  const statSellBuy = document.getElementById("stat-sell-buy");
  const statTotalVolume = document.getElementById("stat-total-volume");

  // Modal Elemanları
  const itemModal = document.getElementById("item-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalItemTitle = document.getElementById("modal-item-title");
  const modalItemSub = document.getElementById("modal-item-sub");
  const modalItemImg = document.getElementById("modal-item-img");
  const modalMinSell = document.getElementById("modal-min-sell");
  const modalMaxBuy = document.getElementById("modal-max-buy");
  const modalSellerCount = document.getElementById("modal-seller-count");
  const modalListingsTbody = document.getElementById("modal-listings-tbody");

  // 1. Genel İstatistikleri Çek
  async function fetchStats() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) return;
      const data = await res.json();
      
      statTotalItems.textContent = (data.total_items || 0).toLocaleString();
      statMerchants.textContent = (data.total_merchants || 0).toLocaleString();
      statSellBuy.textContent = `${data.sell_count || 0} / ${data.buy_count || 0}`;
      statTotalVolume.textContent = `${data.formatted_volume_gb || 0} GB`;
    } catch (err) {
      console.error("Stats çekilemedi:", err);
    }
  }

  // 2. Canlı Pazar Eşyalarını Çek
  async function fetchMarketItems() {
    if (state.isLoading) return;
    state.isLoading = true;

    marketTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; padding: 30px; color: var(--text-muted);">
          <i class="fa-solid fa-spinner fa-spin"></i> Pazar güncelleniyor...
        </td>
      </tr>
    `;

    try {
      const params = new URLSearchParams({
        q: state.q,
        type: state.type,
        category: state.category,
        channel: state.channel,
        sort: state.sort,
        limit: "100"
      });

      const res = await fetch(`/api/market?${params.toString()}`);
      const data = await res.json();
      renderMarketItems(data.items || []);
      resultsCount.textContent = `${data.total || 0} eşya bulundu`;
    } catch (err) {
      marketTbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 30px; color: #ef4444;">
            <i class="fa-solid fa-triangle-exclamation"></i> Veriler yüklenirken bir hata oluştu.
          </td>
        </tr>
      `;
    } finally {
      state.isLoading = false;
    }
  }

  // Pazar Tablosunu Render Et
  function renderMarketItems(items) {
    if (items.length === 0) {
      marketTbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 40px; color: var(--text-muted);">
            <i class="fa-solid fa-box-open" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
            Arama kriterlerinize uygun eşya bulunamadı.
          </td>
        </tr>
      `;
      return;
    }

    marketTbody.innerHTML = items.map(it => {
      const typeBadge = it.market_type === "SELL" 
        ? `<span class="type-badge SELL">SELL</span>` 
        : `<span class="type-badge BUY">BUY</span>`;

      return `
        <tr>
          <td>
            <div class="item-cell">
              <div class="item-icon-box">
                <img src="/icons/${it.icon || 'default.svg'}" alt="${it.item_name}" loading="lazy" onerror="this.src='/icons/default.svg'">
              </div>
              <div class="item-name-wrap">
                <div class="item-title" style="color: ${it.grade_color};" onclick="window.koOpenItem('${escapeQuotes(it.item_name)}')">
                  ${it.item_name}
                </div>
                <div class="item-cat-sub">${it.category}</div>
              </div>
            </div>
          </td>
          <td>${typeBadge}</td>
          <td>
            <div class="price-cell">
              <div class="price-coin">${it.formatted_coin} <span style="font-size: 11px; color: var(--text-dim);">Coin</span></div>
              <div class="price-tag-sub">${it.price_tag}</div>
            </div>
          </td>
          <td>
            <div class="merchant-cell">
              <div class="merchant-info-row">
                <img src="${it.merchant_class_icon || '/static/assets/classes/Human_Warrior.png'}" class="merchant-class-avatar" alt="" onerror="this.style.display='none'">
                <span class="merchant-name">${it.merchant_name}</span>
              </div>
              <span class="merchant-pos">${it.pos_x && it.pos_z ? `X: ${Math.round(it.pos_x)}, Z: ${Math.round(it.pos_z)}` : 'Moradon'}</span>
            </div>
          </td>
          <td>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <span class="channel-tag">${it.server_channel || 'Moradon 1'}</span>
              <span style="font-size: 11px; color: var(--text-dim);">${formatTimeAgo(it.timestamp)}</span>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  }

  // 3. Arbitraj Fırsatlarını Çek
  async function fetchArbitrage() {
    arbitrageTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; padding: 30px; color: var(--text-muted);">
          <i class="fa-solid fa-spinner fa-spin"></i> Arbitraj fırsatları analiz ediliyor...
        </td>
      </tr>
    `;

    try {
      const res = await fetch("/api/arbitrage");
      const data = await res.json();
      renderArbitrage(data.arbitrage || []);
    } catch (err) {
      arbitrageTbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 30px; color: #ef4444;">
            <i class="fa-solid fa-triangle-exclamation"></i> Arbitraj verileri yüklenemedi.
          </td>
        </tr>
      `;
    }
  }

  // Arbitraj Tablosunu Render Et
  function renderArbitrage(list) {
    if (list.length === 0) {
      arbitrageTbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 40px; color: var(--text-muted);">
            <i class="fa-solid fa-scale-balanced" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
            Şu an hem alışı hem satışı bulunan eşya bulunamadı.
          </td>
        </tr>
      `;
      return;
    }

    arbitrageTbody.innerHTML = list.map(a => {
      const isProfitable = a.profit > 0;
      const profitClass = isProfitable ? "positive" : "negative";
      const statusBadge = isProfitable 
        ? `<span class="type-badge SELL" style="font-size: 10px;">KÂRLI</span>` 
        : `<span class="type-badge BUY" style="font-size: 10px; background: rgba(255,255,255,0.05); color: var(--text-muted); border: 1px solid var(--border-subtle);">MAKAS YOK</span>`;

      return `
        <tr>
          <td>
            <div class="item-cell">
              <div class="item-icon-box">
                <img src="/icons/${a.icon || 'default.svg'}" alt="${a.item_name}" loading="lazy" onerror="this.src='/icons/default.svg'">
              </div>
              <div class="item-name-wrap">
                <div class="item-title" onclick="window.koOpenItem('${escapeQuotes(a.item_name)}')">
                  ${a.item_name}
                </div>
                <div class="item-cat-sub">Fırsat Oranı: %${a.margin_percent || 0}</div>
              </div>
            </div>
          </td>
          <td>
            <div class="price-cell">
              <span class="price-coin" style="color: var(--sell-color);">${a.min_sell_fmt}</span>
              <div class="price-tag-sub">En Ucuz Satış</div>
            </div>
          </td>
          <td>
            <div class="price-cell">
              <span class="price-coin" style="color: var(--buy-color);">${a.max_buy_fmt}</span>
              <div class="price-tag-sub">En Yüksek Alış</div>
            </div>
          </td>
          <td>
            <div class="arb-profit ${profitClass}">
              ${isProfitable ? '+' : ''}${a.profit_fmt} Coin
            </div>
            <div style="font-size: 11px; color: var(--text-dim);">Net Fark</div>
          </td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join("");
  }

  // 4. Tezgahları Çek
  async function fetchStalls() {
    stallsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
        <i class="fa-solid fa-spinner fa-spin"></i> Açık tezgahlar yükleniyor...
      </div>
    `;

    try {
      const res = await fetch("/api/stalls");
      const data = await res.json();
      renderStalls(data.stalls || []);
    } catch (err) {
      stallsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #ef4444;">
          <i class="fa-solid fa-triangle-exclamation"></i> Tezgahlar yüklenirken hata oluştu.
        </div>
      `;
    }
  }

  // Tezgah Kartlarını Render Et
  function renderStalls(stalls) {
    if (stalls.length === 0) {
      stallsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
          Açık tezgah bulunamadı.
        </div>
      `;
      return;
    }

    stallsGrid.innerHTML = stalls.map(s => {
      const badge = s.market_type === "SELL"
        ? `<span class="type-badge SELL">SELL</span>`
        : `<span class="type-badge BUY">BUY</span>`;

      // 12 Yuva Doldurma
      const slots = [];
      const items = s.items || [];
      for (let i = 0; i < 12; i++) {
        if (i < items.length) {
          const it = items[i];
          slots.push(`
            <div class="stall-slot" title="${it.item_name} - ${it.price_tag}">
              <img src="/icons/${it.icon || 'default.svg'}" alt="${it.item_name}" loading="lazy" onerror="this.src='/icons/default.svg'">
            </div>
          `);
        } else {
          slots.push(`<div class="stall-slot" style="background: rgba(0,0,0,0.3); border-color: rgba(255,255,255,0.03);"></div>`);
        }
      }

      return `
        <div class="stall-card">
          <div class="stall-header">
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <img src="${s.merchant_class_icon || '/static/assets/classes/Human_Warrior.png'}" class="merchant-class-avatar" alt="" onerror="this.style.display='none'">
                <span class="merchant-name" style="font-size: 15px;">${s.merchant_name}</span>
                ${badge}
              </div>
              <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">
                ${s.server_channel || 'Moradon 1'} • ${s.items_count} Eşya
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-family: var(--font-mono); font-weight: 700; color: var(--gold); font-size: 13px;">
                ${s.formatted_total} Coin
              </div>
              <div style="font-size: 10px; color: var(--text-dim);">Toplam Değer</div>
            </div>
          </div>

          <div class="stall-items-mini">
            ${slots.join("")}
          </div>
        </div>
      `;
    }).join("");
  }

  // 5. Eşya Detay Modalı
  window.koOpenItem = async function(itemName) {
    if (!itemName) return;
    try {
      const res = await fetch(`/api/item/${encodeURIComponent(itemName)}`);
      if (!res.ok) return;
      const data = await res.json();

      modalItemTitle.textContent = data.item_name;
      modalItemSub.textContent = `Toplam ${data.total_sellers} ilan bulundu`;
      
      const firstIcon = (data.listings && data.listings[0] && data.listings[0].icon) ? data.listings[0].icon : 'default.svg';
      modalItemImg.src = `/icons/${firstIcon}`;

      modalMinSell.textContent = data.min_sell ? `${Number(data.min_sell).toLocaleString()} Coin` : '-';
      modalMaxBuy.textContent = data.max_buy ? `${Number(data.max_buy).toLocaleString()} Coin` : '-';
      modalSellerCount.textContent = data.total_sellers || 0;

      if (!data.listings || data.listings.length === 0) {
        modalListingsTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 16px;">İlan bulunamadı.</td></tr>`;
      } else {
        modalListingsTbody.innerHTML = data.listings.map(l => `
          <tr>
            <td><span class="type-badge ${l.market_type}">${l.market_type}</span></td>
            <td><span style="font-family: var(--font-mono); font-weight: 700; color: #fff;">${l.formatted_coin}</span> (${l.price_tag})</td>
            <td><strong>${l.merchant_name}</strong></td>
            <td><span class="channel-tag">${l.server_channel}</span></td>
          </tr>
        `).join("");
      }

      itemModal.classList.add("open");
    } catch (err) {
      console.error("Eşya detayı alınamadı:", err);
    }
  };

  // Modal Kapatma
  function closeModal() {
    itemModal.classList.remove("open");
  }
  if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeModal);
  if (itemModal) {
    itemModal.addEventListener("click", (e) => {
      if (e.target === itemModal) closeModal();
    });
  }

  // 6. Sekme Geçişi
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      if (state.activeTab === tab) return;

      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeTab = tab;

      viewMarket.style.display = tab === "market" ? "block" : "none";
      viewArbitrage.style.display = tab === "arbitrage" ? "block" : "none";
      viewStalls.style.display = tab === "stalls" ? "block" : "none";
      marketFilterBar.style.display = tab === "market" ? "flex" : "none";

      if (tab === "market") fetchMarketItems();
      else if (tab === "arbitrage") fetchArbitrage();
      else if (tab === "stalls") fetchStalls();
    });
  });

  // 7. Filtre Olay Dinleyicileri
  // Arama Girişi (Debounce)
  let searchTimeout = null;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.q = e.target.value.trim();
      fetchMarketItems();
    }, 300);
  });

  // Tür Butonları (Tümü / SELL / BUY)
  typeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      typeBtns.forEach(b => b.classList.remove("active", "sell", "buy"));
      btn.classList.add("active");
      const t = btn.dataset.type;
      if (t === "SELL") btn.classList.add("sell");
      if (t === "BUY") btn.classList.add("buy");
      state.type = t;
      fetchMarketItems();
    });
  });

  // Kategori Hapları
  catPills.forEach(pill => {
    pill.addEventListener("click", () => {
      catPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.category = pill.dataset.category;
      fetchMarketItems();
    });
  });

  // Kanal & Sıralama Dropdownları
  channelSelect.addEventListener("change", (e) => {
    state.channel = e.target.value;
    fetchMarketItems();
  });

  sortSelect.addEventListener("change", (e) => {
    state.sort = e.target.value;
    fetchMarketItems();
  });

  // Yenile Butonu
  refreshBtn.addEventListener("click", () => {
    fetchStats();
    if (state.activeTab === "market") fetchMarketItems();
    else if (state.activeTab === "arbitrage") fetchArbitrage();
    else if (state.activeTab === "stalls") fetchStalls();
  });

  // Yardımcı Fonksiyonlar
  function escapeQuotes(str) {
    if (!str) return "";
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
  }

  function formatTimeAgo(dateStr) {
    if (!dateStr) return "Az önce";
    try {
      const past = new Date(dateStr.replace(" ", "T")).getTime();
      const now = Date.now();
      const diffSec = Math.floor((now - past) / 1000);
      if (isNaN(diffSec) || diffSec < 60) return "Az önce";
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)} dk önce`;
      return `${Math.floor(diffSec / 3600)} sa önce`;
    } catch {
      return "Az önce";
    }
  }

  // İlk Başlatma
  fetchStats();
  fetchMarketItems();

  // 15 saniyede bir sayaçları güncelle
  setInterval(fetchStats, 15000);
});
