<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget Slider Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
          <div class="budget-display">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
        </div>
        <div class="budget-slider-container">
          <input
            v-model.number="budget"
            type="range"
            min="0"
            max="2000000"
            step="10000"
            class="budget-range"
          />
          <div class="budget-labels">
            <span>{{ currencySymbol }}0</span>
            <span>{{ currencySymbol }}2,000,000</span>
          </div>
          <div class="budget-bar-track">
            <div
              class="budget-bar-fill"
              :style="{ width: Math.min((totalCost / budget) * 100, 100) + '%', background: budgetRemaining < 0 ? '#ef4444' : '#3b82f6' }"
            ></div>
          </div>
          <div class="budget-bar-labels">
            <span class="budget-used-label">
              {{ currencySymbol }}{{ totalCost.toLocaleString() }} used
            </span>
            <span
              class="budget-remaining-label"
              :style="{ color: budgetRemaining < 0 ? '#ef4444' : '#059669' }"
            >
              {{ budgetRemaining >= 0 ? currencySymbol + budgetRemaining.toLocaleString() + ' remaining' : currencySymbol + Math.abs(budgetRemaining).toLocaleString() + ' over budget' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.itemsToRestock') }}</div>
          <div class="stat-value">{{ recommendations.length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
        </div>
        <div class="stat-card" :class="budgetRemaining >= 0 ? 'success' : 'danger'">
          <div class="stat-label">{{ t('restocking.budgetRemaining') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ Math.abs(budgetRemaining).toLocaleString() }}</div>
        </div>
      </div>

      <!-- Recommendations Table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendations.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="submitting || recommendations.length === 0 || !!submittedOrder"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div class="table-container">
          <table class="restocking-table">
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.recommendedQty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.totalCost') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td>{{ item.quantity_on_hand }}</td>
                <td><strong>{{ item.recommended_quantity }}</strong></td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>{{ currencySymbol }}{{ item.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</strong></td>
                <td>
                  <span :class="['badge', item.trend]">
                    {{ t(`trends.${item.trend}`) }}
                  </span>
                </td>
              </tr>
              <tr v-if="recommendations.length === 0">
                <td colspan="8" class="no-data-cell">{{ t('restocking.noRecommendations') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Success Message -->
      <div v-if="submittedOrder" class="card success-card">
        <div class="card-header">
          <h3 class="card-title success-title">{{ t('restocking.orderPlaced') }}</h3>
        </div>
        <div class="success-details">
          <div class="success-detail-item">
            <span class="success-detail-label">{{ t('restocking.orderNumber') }}</span>
            <span class="success-detail-value">{{ submittedOrder.order_number }}</span>
          </div>
          <div class="success-detail-item">
            <span class="success-detail-label">{{ t('restocking.leadTime') }}</span>
            <span class="success-detail-value">{{ submittedOrder.lead_time_days }} {{ t('restocking.days') }}</span>
          </div>
          <div class="success-detail-item">
            <span class="success-detail-label">{{ t('restocking.expectedDelivery') }}</span>
            <span class="success-detail-value">{{ formatDate(submittedOrder.expected_delivery) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const currencySymbol = computed(() => currentCurrency.value === 'JPY' ? '¥' : '$')

    const loading = ref(true)
    const error = ref(null)
    const recommendations = ref([])
    const budget = ref(500000)
    const submitting = ref(false)
    const submittedOrder = ref(null)

    const totalCost = computed(() =>
      recommendations.value.reduce((sum, r) => sum + r.total_cost, 0)
    )

    const budgetRemaining = computed(() => budget.value - totalCost.value)

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        recommendations.value = await api.getRestockingRecommendations(budget.value)
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    let debounceTimer = null
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        submittedOrder.value = null
        loadRecommendations()
      }, 300)
    })

    const placeOrder = async () => {
      try {
        submitting.value = true
        error.value = null
        const orderData = {
          items: recommendations.value.map(r => ({
            item_sku: r.item_sku,
            item_name: r.item_name,
            quantity: r.recommended_quantity,
            unit_cost: r.unit_cost
          })),
          total_budget: totalCost.value
        }
        submittedOrder.value = await api.submitRestockingOrder(orderData)
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      loading,
      error,
      recommendations,
      budget,
      submitting,
      submittedOrder,
      totalCost,
      budgetRemaining,
      placeOrder,
      formatDate
    }
  }
}
</script>

<style scoped>
.budget-slider-container {
  padding: 0.5rem 0.25rem 0.75rem;
}

.budget-display {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-range {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
  accent-color: #3b82f6;
  margin-bottom: 0.5rem;
}

.budget-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
  transition: box-shadow 0.2s;
}

.budget-range::-webkit-slider-thumb:hover {
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.budget-range::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
  transition: box-shadow 0.2s;
}

.budget-range::-moz-range-thumb:hover {
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.budget-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 1.25rem;
}

.budget-bar-track {
  width: 100%;
  height: 8px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.budget-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background 0.3s ease;
  min-width: 0;
}

.budget-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
}

.budget-used-label {
  color: #64748b;
  font-weight: 500;
}

.budget-remaining-label {
  font-weight: 600;
  transition: color 0.2s;
}

.place-order-btn {
  background: #3b82f6;
  color: #ffffff;
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
  white-space: nowrap;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.restocking-table {
  table-layout: fixed;
  width: 100%;
}

.restocking-table th:nth-child(1) { width: 8%; }
.restocking-table th:nth-child(2) { width: 22%; }
.restocking-table th:nth-child(3) { width: 12%; }
.restocking-table th:nth-child(4) { width: 9%; }
.restocking-table th:nth-child(5) { width: 13%; }
.restocking-table th:nth-child(6) { width: 10%; }
.restocking-table th:nth-child(7) { width: 12%; }
.restocking-table th:nth-child(8) { width: 14%; }

.no-data-cell {
  text-align: center;
  padding: 2.5rem 1rem;
  color: #94a3b8;
  font-size: 0.938rem;
}

.success-card {
  border-left: 4px solid #22c55e;
  background: #f0fdf4;
}

.success-title {
  color: #15803d;
}

.success-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.25rem;
  padding: 0.25rem 0;
}

.success-detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.success-detail-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.success-detail-value {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}
</style>
