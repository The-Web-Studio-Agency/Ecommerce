import Header from "./Header"

interface Props {
    children: React.ReactNode 
}

const WithoutFooterLayout = ({children} : Props) =>{
    return(
        <div className="page-wraper">
            <Header design=""/>
            {children}
        </div>
    )
}
export default WithoutFooterLayout;