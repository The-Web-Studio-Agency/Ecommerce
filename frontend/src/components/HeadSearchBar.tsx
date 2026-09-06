import Link from "next/link";
import SearchCategorySlider from "./SearchCategorySlider";
import Categorydropdown from "./CategoryDropdown";

export default function HeadSearchBar(){    
    return(
        <div className="container">
            <form className="header-item-search">
                <div className="input-group search-input">               
                    <Categorydropdown />                  
                    <input type="search" className="form-control" placeholder="Search Product" />
                    <button className="btn" type="button">
                        <i className="iconly-Light-Search"/>
                    </button>
                </div>
                <ul className="recent-tag">
                    <li className="pe-0"><span>Quick Search :</span></li>
                    <li><Link href="/shop-list">Clothes</Link></li>
                    <li><Link href="/shop-list">UrbanSkirt</Link></li>
                    <li><Link href="/shop-list">VelvetGown</Link></li>
                    <li><Link href="/shop-list">LushShorts</Link></li>
                </ul>
            </form>
            <div className="row">
                <div className="col-xl-12">
                    <h5 className="mb-3">You May Also Like</h5>                    
                    <SearchCategorySlider />
                </div>
            </div>
        </div>
    )
}