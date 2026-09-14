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
tempfile SI
save `SI'


* This is LIST-8R ACTIVE from https://www.epa.gov/superfund/superfund-data-and-reports
import excel "${dir1}/406340.xlsx", clear firstrow
keep EPAID LATITUDE LONGITUDE NPL STREETADDRESS* CITY STATE ZIP COUNTY FIPSCODE
gen list8r = "active"

tempfile active
save `active'

* This is LIST-8R ARCHIVED from https://www.epa.gov/superfund/superfund-data-and-reports
import excel "${dir1}/406341.xlsx", clear firstrow
keep EPAID NPL STREETADDRESS* CITY STATE ZIP COUNTY FIPSCODE
gen list8r = "archived"
append using `active'

gen npl01 = strpos(NPL,"Final NPL") > 0 | NPL == "Site is Part of NPL Site"

drop NPL
bys EPAID: keep if _n==1
merge 1:1 EPAID using `SI'

gen SIqual = _merge==3
drop _merge
export delimited "${dir1}/sitelist_nogeocodes.csv", replace


*** Code used to make rough first version 
/*
cd "~/Documents/VS Code/CERCLIS"
import delimited "CERCLIS_Geocoded.csv", clear
keep x y user_epaid 
tempfile allsites
save `allsites'
import excel "~/Google Drive/My Drive/Superfund-search/data/raw/federal/NPlgeocoordinates.xlsx", clear
keep A
rename A user_epaid
merge 1:1 user_epaid using `allsites'
gen indicator = (_merge==3)
rename user_epaid epaid
drop _merge
replace x = . if x==0
replace y = . if y==0
export delimited "~/Google Drive/My Drive/contamination project/MOSAIKS/superfund_project_summer2026/Data/Raw/cerclis_geocoded_windicator.csv", replace
*/
