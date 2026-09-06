import CommanLayout from "@/components/CommanLayout";
import { Fragment } from "react"
import ShopProductCarousel from "./_components/ShopProductCarousel";

const ShopProductCarouselPage = () =>{
    return(
        <Fragment>
            <CommanLayout>
                <ShopProductCarousel />
            </CommanLayout>
        </Fragment>
    )
}
export default ShopProductCarouselPage;