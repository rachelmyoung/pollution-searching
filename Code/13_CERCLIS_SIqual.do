global dir1 "~/Google Drive/My Drive/contamination project/MOSAIKS/superfund_project_summer2026/data/raw/CERCLIS"

clear
tempfile all
save `all', emptyok

* LIST-008 (Archived)
foreach region in 1 2 3 4 5 6 7 8 9 10 {
	import excel "${dir1}/406341.xlsx", sheet("Region `region'") clear first
	keep if ACTIONCODE=="SI"
	append using `all'
	save `all', replace
}

* LIST-008 (Active)
foreach region in 1 2 3 4 5 6 7 8 9 10 {
	import excel "${dir1}/406340.xlsx", sheet("Region `region'") clear first
	keep if ACTIONCODE=="SI"
	append using `all'
	save `all', replace
}

keep if inlist(QUAL,"H","L")
keep EPAID
bys EPAID: keep if _n==1
rename EPAID epaid
tempfile SI
save `SI'

import delimited "~/Documents/Github/pollution-searching/data/raw/cerclis_geocoded_windicator.csv", clear

bys epaid: keep if _n==1

merge 1:1 epaid using `SI'

gen indicator_si = _merge==3
drop _merge

drop indicator
rename indicator_si indicator

export delimited "~/Documents/Github/pollution-searching/data/raw/cerclis_geocoded_windicator_si.csv", replace
