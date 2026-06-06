import { api } from "./api";
import {
  CategoriesAnalyticsResponse,
  MonthlyExpensesResponse,
  PurchaseHabitsResponse,
} from "@/src/types/analytics";

export const analyticsService = {
  async getMonthlyExpenses(year: number, month: number) {
    const { data } = await api.get<MonthlyExpensesResponse>(
      "/analytics/monthly-expenses",
      {
        params: { year, month },
      }
    );

    return data;
  },

  async getCategories(year: number, month: number) {
    const { data } = await api.get<CategoriesAnalyticsResponse>(
      "/analytics/categories",
      {
        params: { year, month },
      }
    );

    return data;
  },

  async getHabits() {
    const { data } = await api.get<PurchaseHabitsResponse>("/analytics/habits");
    return data;
  },
};
