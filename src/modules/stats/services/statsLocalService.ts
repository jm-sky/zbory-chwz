/**
 * Stats Local Service
 * Calculates statistics from localStorage data
 * NOTE: Gear-related functionality has been stubbed out
 */
class StatsLocalService {
  /**
   * Get current month start date
   */
  private getCurrentMonthStart(): Date {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  }

  /**
   * Check if date is within current month
   */
  private isThisMonth(dateString: string): boolean {
    const date = new Date(dateString)
    const monthStart = this.getCurrentMonthStart()
    return date >= monthStart
  }

  /**
   * Get user statistics
   * Note: Users are not stored locally, so this always returns 0
   */
  async getUserStats(): Promise<{ total: number; newThisMonth: number }> {
    return { total: 0, newThisMonth: 0 }
  }

  /**
   * Get container statistics from localStorage
   * STUB: Gear store removed - always returns 0
   */
  async getContainerStats(): Promise<{ total: number; newThisMonth: number }> {
    console.warn('getContainerStats called but gear module is not available')
    return { total: 0, newThisMonth: 0 }
  }

  /**
   * Get item statistics from localStorage
   * STUB: Gear store removed - always returns 0
   */
  async getItemStats(): Promise<{ total: number; newThisMonth: number }> {
    console.warn('getItemStats called but gear module is not available')
    return { total: 0, newThisMonth: 0 }
  }

  /**
   * Get all statistics
   */
  async getAllStats(): Promise<{
    users: { total: number; newThisMonth: number }
    containers: { total: number; newThisMonth: number }
    items: { total: number; newThisMonth: number }
  }> {
    const [users, containers, items] = await Promise.all([
      this.getUserStats(),
      this.getContainerStats(),
      this.getItemStats(),
    ])

    return { users, containers, items }
  }
}

export const statsLocalService = new StatsLocalService()
