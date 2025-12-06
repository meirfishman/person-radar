/**
 * Person Radar - Dashboard JavaScript
 */

// State
let currentDays = 7;
let showViewed = true;

// DOM elements
const contentArea = document.getElementById('content-area');
const statsBar = document.getElementById('stats-bar');
const daysFilter = document.getElementById('days-filter');
const showViewedCheckbox = document.getElementById('show-viewed');
const refreshBtn = document.getElementById('refresh-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadContent();
    loadStats();
    setupEventListeners();
});

function setupEventListeners() {
    daysFilter.addEventListener('change', (e) => {
        currentDays = parseInt(e.target.value);
        loadContent();
    });

    showViewedCheckbox.addEventListener('change', (e) => {
        showViewed = e.target.checked;
        loadContent();
    });

    refreshBtn.addEventListener('click', refreshData);
}

async function loadContent() {
    contentArea.innerHTML = '<div class="loading">Loading content...</div>';

    try {
        const response = await fetch(
            `/api/content?days=${currentDays}&include_viewed=${showViewed}`
        );
        const data = await response.json();
        renderContent(data);
    } catch (error) {
        console.error('Error loading content:', error);
        contentArea.innerHTML = '<div class="loading">Error loading content. Please try again.</div>';
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        renderStats(stats);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function renderStats(stats) {
    const items = [
        `<span class="stat"><strong>${stats.total || 0}</strong> total items</span>`,
        `<span class="stat"><strong>${stats.unviewed || 0}</strong> unread</span>`,
    ];

    if (stats.by_type) {
        if (stats.by_type.youtube) {
            items.push(`<span class="stat"><strong>${stats.by_type.youtube}</strong> YouTube</span>`);
        }
        if (stats.by_type.twitter) {
            items.push(`<span class="stat"><strong>${stats.by_type.twitter}</strong> Twitter</span>`);
        }
        if (stats.by_type.news) {
            items.push(`<span class="stat"><strong>${stats.by_type.news}</strong> News</span>`);
        }
    }

    statsBar.innerHTML = items.join('');
}

function renderContent(groupedContent) {
    if (Object.keys(groupedContent).length === 0) {
        contentArea.innerHTML = `
            <div class="loading">
                No content found. Try running the update script or adjusting the time filter.
            </div>
        `;
        return;
    }

    // Sort people by number of items (most first)
    const sortedPeople = Object.entries(groupedContent)
        .sort((a, b) => b[1].length - a[1].length);

    const html = sortedPeople.map(([person, items]) => {
        return renderPersonSection(person, items);
    }).join('');

    contentArea.innerHTML = html;
}

function renderPersonSection(person, items) {
    const unviewedCount = items.filter(i => !i.viewed).length;
    const countText = unviewedCount > 0
        ? `${unviewedCount} new / ${items.length} total`
        : `${items.length} items`;

    const itemsHtml = items.length > 0
        ? items.map(item => renderContentItem(item)).join('')
        : '<div class="empty-message">No recent updates</div>';

    return `
        <section class="person-section">
            <div class="person-header">
                <h2>${escapeHtml(person)}</h2>
                <span class="count">${countText}</span>
            </div>
            <div class="person-content">
                ${itemsHtml}
            </div>
        </section>
    `;
}

function renderContentItem(item) {
    const viewedClass = item.viewed ? 'viewed' : '';
    const thumbnail = renderThumbnail(item);
    const typeIcon = getTypeIcon(item.content_type);
    const date = formatDate(item.date_published || item.date_found);

    return `
        <div class="content-item ${viewedClass}" data-id="${item.id}">
            <div class="item-thumbnail">
                ${thumbnail}
            </div>
            <div class="item-body">
                <div class="item-header">
                    <span class="item-type ${item.content_type}">${item.content_type}</span>
                    <div class="item-title">
                        <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">
                            ${escapeHtml(item.title)}
                        </a>
                    </div>
                </div>
                <div class="item-meta">
                    ${item.source_channel ? `<span>${escapeHtml(item.source_channel)}</span>` : ''}
                    <span>${date}</span>
                </div>
                ${item.description ? `<div class="item-description">${escapeHtml(item.description)}</div>` : ''}
            </div>
            <div class="item-actions">
                <button class="btn-viewed ${item.viewed ? 'is-viewed' : ''}"
                        onclick="toggleViewed(${item.id}, ${item.viewed})">
                    ${item.viewed ? 'Viewed' : 'Mark viewed'}
                </button>
            </div>
        </div>
    `;
}

function renderThumbnail(item) {
    if (item.thumbnail_url) {
        return `<img src="${escapeHtml(item.thumbnail_url)}" alt="" loading="lazy">`;
    }

    const icon = getTypeIcon(item.content_type);
    return `<div class="placeholder">${icon}</div>`;
}

function getTypeIcon(type) {
    switch (type) {
        case 'youtube': return '&#9654;';
        case 'twitter': return '&#128172;';
        case 'news': return '&#128240;';
        default: return '&#128196;';
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';

    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        if (diffHours === 0) {
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            return `${diffMinutes}m ago`;
        }
        return `${diffHours}h ago`;
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        });
    }
}

async function toggleViewed(id, currentState) {
    const endpoint = currentState ? 'unviewed' : 'viewed';

    try {
        const response = await fetch(`/api/content/${id}/${endpoint}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            // Update the UI
            const item = document.querySelector(`.content-item[data-id="${id}"]`);
            if (item) {
                const btn = item.querySelector('.btn-viewed');
                if (currentState) {
                    item.classList.remove('viewed');
                    btn.classList.remove('is-viewed');
                    btn.textContent = 'Mark viewed';
                } else {
                    item.classList.add('viewed');
                    btn.classList.add('is-viewed');
                    btn.textContent = 'Viewed';
                }
            }
            // Refresh stats
            loadStats();
        }
    } catch (error) {
        console.error('Error toggling viewed status:', error);
    }
}

async function refreshData() {
    refreshBtn.disabled = true;
    refreshBtn.textContent = 'Refreshing...';

    try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            refreshBtn.textContent = `Added ${data.new_items} items`;
            setTimeout(() => {
                refreshBtn.textContent = 'Refresh Data';
                refreshBtn.disabled = false;
            }, 2000);
            // Reload content
            loadContent();
            loadStats();
        } else {
            throw new Error(data.error || 'Refresh failed');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        refreshBtn.textContent = 'Refresh failed';
        setTimeout(() => {
            refreshBtn.textContent = 'Refresh Data';
            refreshBtn.disabled = false;
        }, 2000);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
