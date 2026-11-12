<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { currentDate, availableDates, hasDataForDate, navigateToDate } from '$lib/stores/dateStore';
	import {
		getCalendarGrid,
		isInMonth,
		isToday,
		isSameDay,
		toDateString,
		getMonthName,
		getWeekdayNames,
		parseDate
	} from '$lib/services/dateUtils';
	import CalendarDay from './CalendarDay.svelte';

	const dispatch = createEventDispatcher();

	// Current view month/year
	let viewYear = new Date().getFullYear();
	let viewMonth = new Date().getMonth();

	// Initialize to current date's month when it changes
	$: if ($currentDate) {
		const date = parseDate($currentDate);
		if (date) {
			viewYear = date.getFullYear();
			viewMonth = date.getMonth();
		}
	}

	$: calendarDays = getCalendarGrid(viewYear, viewMonth);
	$: monthName = getMonthName(viewMonth);
	$: weekdays = getWeekdayNames();
	$: hasData = $hasDataForDate;

	function previousMonth() {
		if (viewMonth === 0) {
			viewMonth = 11;
			viewYear--;
		} else {
			viewMonth--;
		}
	}

	function nextMonth() {
		if (viewMonth === 11) {
			viewMonth = 0;
			viewYear++;
		} else {
			viewMonth++;
		}
	}

	function selectDate(date: Date) {
		const dateStr = toDateString(date);
		if (hasData(dateStr)) {
			navigateToDate(dateStr);
			dispatch('select', { date: dateStr });
		}
	}
</script>

<div class="bg-papel border border-filete p-4 font-sans">
	<!-- Header with month navigation -->
	<div class="flex items-center justify-between mb-4">
		<button
			on:click={previousMonth}
			class="p-2 rounded-lg hover:bg-radar-gray-100 dark:hover:bg-radar-gray-700 transition-colors"
			aria-label="Mes anterior"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-5 h-5"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
				stroke-width="2"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
			</svg>
		</button>

		<h3 class="font-semibold text-radar-gray-800 dark:text-radar-gray-200">
			{monthName} {viewYear}
		</h3>

		<button
			on:click={nextMonth}
			class="p-2 rounded-lg hover:bg-radar-gray-100 dark:hover:bg-radar-gray-700 transition-colors"
			aria-label="Mes siguiente"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-5 h-5"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
				stroke-width="2"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
			</svg>
		</button>
	</div>

	<!-- Weekday headers -->
	<div class="grid grid-cols-7 mb-2">
		{#each weekdays as day}
			<div class="text-center text-xs font-medium text-radar-gray-500 dark:text-radar-gray-400 py-2">
				{day}
			</div>
		{/each}
	</div>

	<!-- Calendar grid -->
	<div class="grid grid-cols-7 gap-1">
		{#each calendarDays as day}
			{@const dateStr = toDateString(day)}
			{@const inMonth = isInMonth(day, viewYear, viewMonth)}
			{@const today = isToday(day)}
			{@const selected = $currentDate === dateStr}
			{@const available = hasData(dateStr)}

			<CalendarDay
				{day}
				{inMonth}
				{today}
				{selected}
				{available}
				on:click={() => selectDate(day)}
			/>
		{/each}
	</div>

	<!-- Legend -->
	<div class="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-radar-gray-200 dark:border-radar-gray-700 text-xs text-radar-gray-500">
		<div class="flex items-center gap-1.5">
			<span class="w-3 h-3 rounded-full bg-radar-accent"></span>
			<span>Con edición</span>
		</div>
		<div class="flex items-center gap-1.5">
			<span class="w-3 h-3 rounded-full border-2 border-radar-accent"></span>
			<span>Hoy</span>
		</div>
	</div>
</div>
